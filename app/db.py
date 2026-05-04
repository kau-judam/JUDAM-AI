"""
DB 연결 모듈
asyncpg를 활용한 비동기 PostgreSQL 연결
"""

import logging
import os
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager
import asyncpg
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """데이터베이스 연결 관리자"""

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """데이터베이스 연결"""
        if not self.database_url:
            logger.warning("DATABASE_URL이 설정되지 않음")
            return

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("데이터베이스 연결 완료")
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise

    async def disconnect(self):
        """데이터베이스 연결 해제"""
        if self.pool:
            await self.pool.close()
            logger.info("데이터베이스 연결 해제")

    @asynccontextmanager
    async def get_connection(self):
        """연결 컨텍스트 매니저"""
        if not self.pool:
            raise RuntimeError("데이터베이스 연결이 되지 않았습니다")

        async with self.pool.acquire() as connection:
            yield connection

    async def execute(self, query: str, *args) -> str:
        """
        쿼리 실행 (INSERT, UPDATE, DELETE)

        Args:
            query: SQL 쿼리
            *args: 쿼리 파라미터

        Returns:
            실행 결과
        """
        async with self.get_connection() as conn:
            result = await conn.execute(query, *args)
            return result

    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """
        쿼리 실행 및 결과 반환 (SELECT)

        Args:
            query: SQL 쿼리
            *args: 쿼리 파라미터

        Returns:
            쿼리 결과 리스트
        """
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """
        쿼리 실행 및 단일 결과 반환 (SELECT)

        Args:
            query: SQL 쿼리
            *args: 쿼리 파라미터

        Returns:
            쿼리 결과 (단일)
        """
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def initialize_tables(self):
        """테이블 초기화"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS drinks (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                abv FLOAT,
                brewery VARCHAR(100),
                region VARCHAR(50),
                description TEXT,
                features TEXT,
                ingredients TEXT,
                awards TEXT,
                taste_vector JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_taste_history (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
                drink_id VARCHAR(50) REFERENCES drinks(id) ON DELETE CASCADE,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                tags TEXT[],
                taste_vector JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS recommendations (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
                drink_id VARCHAR(50) REFERENCES drinks(id) ON DELETE CASCADE,
                similarity FLOAT,
                context JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS food_pairings (
                id SERIAL PRIMARY KEY,
                food_name VARCHAR(100) NOT NULL,
                drink_id VARCHAR(50) REFERENCES drinks(id) ON DELETE CASCADE,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_user_taste_history_user_id ON user_taste_history(user_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON recommendations(user_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_food_pairings_food_name ON food_pairings(food_name)
            """
        ]

        for table_sql in tables:
            try:
                await self.execute(table_sql)
            except Exception as e:
                logger.error(f"테이블 생성 실패: {e}")

        logger.info("테이블 초기화 완료")

    async def insert_drink(self, drink_data: Dict) -> str:
        """
        전통주 데이터 삽입

        Args:
            drink_data: 전통주 데이터

        Returns:
            삽입된 ID
        """
        query = """
        INSERT INTO drinks (id, name, abv, brewery, region, description, features, ingredients, awards, taste_vector)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            abv = EXCLUDED.abv,
            brewery = EXCLUDED.brewery,
            region = EXCLUDED.region,
            description = EXCLUDED.description,
            features = EXCLUDED.features,
            ingredients = EXCLUDED.ingredients,
            awards = EXCLUDED.awards,
            taste_vector = EXCLUDED.taste_vector,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """

        result = await self.fetchrow(
            query,
            drink_data['id'],
            drink_data['name'],
            drink_data.get('abv'),
            drink_data.get('brewery'),
            drink_data.get('region'),
            drink_data.get('description'),
            drink_data.get('features'),
            drink_data.get('ingredients'),
            drink_data.get('awards'),
            json.dumps(drink_data.get('taste_vector', {}))
        )

        return result['id'] if result else None

    async def get_drink(self, drink_id: str) -> Optional[Dict]:
        """
        전통주 데이터 조회

        Args:
            drink_id: 전통주 ID

        Returns:
            전통주 데이터
        """
        query = "SELECT * FROM drinks WHERE id = $1"
        return await self.fetchrow(query, drink_id)

    async def get_all_drinks(self) -> List[Dict]:
        """
        모든 전통주 데이터 조회

        Returns:
            전통주 데이터 리스트
        """
        query = "SELECT * FROM drinks ORDER BY name"
        return await self.fetch(query)

    async def insert_user(self, user_data: Dict) -> str:
        """
        사용자 데이터 삽입

        Args:
            user_data: 사용자 데이터

        Returns:
            삽입된 ID
        """
        query = """
        INSERT INTO users (id, name, email)
        VALUES ($1, $2, $3)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """

        result = await self.fetchrow(
            query,
            user_data['id'],
            user_data.get('name'),
            user_data.get('email')
        )

        return result['id'] if result else None

    async def insert_taste_history(self, history_data: Dict) -> int:
        """
        취향 히스토리 삽입

        Args:
            history_data: 취향 히스토리 데이터

        Returns:
            삽입된 ID
        """
        query = """
        INSERT INTO user_taste_history (user_id, drink_id, rating, tags, taste_vector)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """

        result = await self.fetchrow(
            query,
            history_data['user_id'],
            history_data['drink_id'],
            history_data['rating'],
            history_data.get('tags', []),
            json.dumps(history_data.get('taste_vector', {}))
        )

        return result['id'] if result else None

    async def get_user_taste_history(self, user_id: str) -> List[Dict]:
        """
        사용자 취향 히스토리 조회

        Args:
            user_id: 사용자 ID

        Returns:
            취향 히스토리 리스트
        """
        query = """
        SELECT * FROM user_taste_history
        WHERE user_id = $1
        ORDER BY created_at DESC
        """
        return await self.fetch(query, user_id)

    async def get_similar_drinks(self, taste_vector: Dict, limit: int = 10) -> List[Dict]:
        """
        맛 벡터 기반 유사 전통주 조회

        Args:
            taste_vector: 맛 벡터
            limit: 반환할 개수

        Returns:
            유사 전통주 리스트
        """
        # 간단한 코사인 유사도 계산 (애플리케이션 레벨에서 처리)
        query = """
        SELECT * FROM drinks
        WHERE taste_vector IS NOT NULL
        LIMIT 100
        """
        all_drinks = await self.fetch(query)

        # 코사인 유사도 계산
        def cosine_similarity(vec1: Dict, vec2: Dict) -> float:
            axes = ['sweetness', 'body', 'carbonation', 'flavor', 'alcohol', 'acidity', 'aroma_intensity', 'finish']
            dot_product = sum(vec1.get(axis, 0) * vec2.get(axis, 0) for axis in axes)
            norm1 = sum(vec1.get(axis, 0) ** 2 for axis in axes) ** 0.5
            norm2 = sum(vec2.get(axis, 0) ** 2 for axis in axes) ** 0.5

            if norm1 == 0 or norm2 == 0:
                return 0.0
            return dot_product / (norm1 * norm2)

        # 유사도 계산 및 정렬
        similar_drinks = []
        for drink in all_drinks:
            drink_vector = drink.get('taste_vector', {})
            similarity = cosine_similarity(taste_vector, drink_vector)
            similar_drinks.append({**drink, 'similarity': similarity})

        similar_drinks.sort(key=lambda x: x['similarity'], reverse=True)

        return similar_drinks[:limit]


# 전역 DB 인스턴스
db = Database()


async def get_db():
    """DB 의존성 주입용"""
    return db


def main():
    """메인 실행 함수"""
    import asyncio

    async def test():
        try:
            # 연결
            await db.connect()

            # 테이블 초기화
            await db.initialize_tables()

            # 샘플 데이터 삽입
            sample_drink = {
                'id': 'test_drink_001',
                'name': '테스트 막걸리',
                'abv': 6.0,
                'brewery': '테스트 양조장',
                'region': '경기도',
                'description': '테스트용 막걸리',
                'features': '테스트',
                'ingredients': '쌀, 누룩, 물',
                'awards': '',
                'taste_vector': {
                    'sweetness': 5.0,
                    'body': 5.0,
                    'carbonation': 5.0,
                    'flavor': 5.0,
                    'alcohol': 5.0,
                    'acidity': 5.0,
                    'aroma_intensity': 5.0,
                    'finish': 5.0
                }
            }

            drink_id = await db.insert_drink(sample_drink)
            print(f"삽입된 전통주 ID: {drink_id}")

            # 조회
            drink = await db.get_drink(drink_id)
            print(f"조회된 전통주: {drink}")

            # 모든 전통주 조회
            all_drinks = await db.get_all_drinks()
            print(f"총 전통주 수: {len(all_drinks)}")

        except Exception as e:
            print(f"테스트 실패: {e}")
        finally:
            await db.disconnect()

    asyncio.run(test())


if __name__ == "__main__":
    main()
