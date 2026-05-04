"""
전통주 RAG DB 모듈
전통주 전문 문서 벡터 DB 구축 및 검색
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from pydantic import BaseModel
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGDocument(BaseModel):
    """RAG 문서 모델"""
    id: str
    title: str
    content: str
    source: str
    category: str
    metadata: Dict


class RAGSearchRequest(BaseModel):
    """RAG 검색 요청 모델"""
    query: str
    top_k: int = 5
    category: Optional[str] = None


class RAGSearchResponse(BaseModel):
    """RAG 검색 응답 모델"""
    query: str
    results: List[Dict]
    total: int


class TraditionalAlcoholRAG:
    """전통주 RAG 시스템"""

    def __init__(self, db_path: str = "rag_db"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(exist_ok=True)

        # 문서 저장소
        self.documents = []
        self.document_index = defaultdict(list)

        # TF-IDF 벡터라이저 (간단 구현)
        self.vocabulary = set()
        self.document_vectors = {}

        # 초기화
        self._initialize_sample_documents()

    def _initialize_sample_documents(self):
        """샘플 문서 초기화"""
        sample_docs = [
            {
                "id": "doc_001",
                "title": "막걸리의 역사",
                "content": """
막걸리는 한국의 대표적인 전통주로, 삼국시대부터 제조되어 온 술입니다.
고려시대에는 '막걸리'라는 이름이 처음 등장했으며, 조선시대에는 서민들의 대중적인 술로 자리 잡았습니다.
막걸리는 쌀, 누룩, 물을 주재료로 하여 발효시킨 탁주로, 영양가가 풍부하고 소화가 잘 되는 특징이 있습니다.
""",
                "source": "전통주갤러리",
                "category": "역사",
                "metadata": {"period": "삼국시대~조선시대", "keywords": ["막걸리", "역사", "탁주"]}
            },
            {
                "id": "doc_002",
                "title": "막걸리 제조 방법",
                "content": """
막걸리 제조의 핵심은 누룩과 쌀의 비율, 그리고 발효 온도 조절입니다.
기본적인 제조 과정은 다음과 같습니다:
1. 쌀을 쪄서 식힙니다
2. 누룩과 물을 섞어 발효시킵니다
3. 적절한 온도(15-20도)에서 3-7일간 발酵시킵니다
4. 걸러서 막걸리를 완성합니다

지역에 따라 제조 방법이 다양하며, 경기도, 강원도, 경상도 등 각 지역만의 특징이 있습니다.
""",
                "source": "더술닷컴",
                "category": "제조",
                "metadata": {"keywords": ["막걸리", "제조", "누룩", "발효"]}
            },
            {
                "id": "doc_003",
                "title": "전통주의 종류",
                "content": """
한국의 전통주는 크게 탁주, 약주, 소주로 나뉩니다.

탁주: 막걸리가 대표적이며, 걸러지지 않은 상태로 쌀알이 섞여 있습니다.
약주: 청주, 향옥 등이 있으며, 맑게 걸러진 술입니다.
소주: 증류주로, 고려시대 몽골의 영향으로 전래되었습니다.

그 외에도 과실주(매실주, 복분자주 등), 약주(동동주, 사과주 등) 등 다양한 전통주가 있습니다.
""",
                "source": "농촌진흥청",
                "category": "종류",
                "metadata": {"keywords": ["전통주", "탁주", "약주", "소주", "과실주"]}
            },
            {
                "id": "doc_004",
                "title": "막걸리와 음식 페어링",
                "content": """
막걸리는 다양한 한국 음식과 잘 어울립니다.

갈비찜, 삼겹살 등 고기 요리: 묵직한 막걸리가 잘 어울립니다
회, 초밥 등 생선 요리: 산미가 있는 막걸리가 좋습니다
파전, 떡볶이 등 매운 음식: 탄산감이 있는 막걸리가 매운맛을 잡아줍니다
김치찌개, 된장찌개 등 찌개: 밸런스형 막걸리가 잘 어울립니다

지역별로도 특색 있는 페어링이 있습니다. 경기도 막걸리는 갈비찜과, 강원도 막걸리는 감자전과 잘 어울립니다.
""",
                "source": "전통주갤러리",
                "category": "페어링",
                "metadata": {"keywords": ["막걸리", "페어링", "음식", "안주"]}
            },
            {
                "id": "doc_005",
                "title": "전통주 보관 방법",
                "content": """
전통주는 적절한 보관 방법이 중요합니다.

온도: 4-10도의 저온 보관이 좋습니다
빛: 직사광선을 피하고 어두운 곳에 보관합니다
밀봉: 공기와의 접촉을 최소화하기 위해 밀봉을 잘해야 합니다
기간: 개봉 후 3-5일 내에 섭취하는 것이 좋습니다

막걸리는 발효가 계속되므로, 시간이 지나면 맛이 변할 수 있습니다.
냉장 보관하더라도 1주일 이내에 드시는 것을 권장합니다.
""",
                "source": "더술닷컴",
                "category": "보관",
                "metadata": {"keywords": ["전통주", "보관", "막걸리", "온도"]}
            },
            {
                "id": "doc_006",
                "title": "지역별 막걸리 특징",
                "content": """
한국의 각 지역은 독특한 막걸리 전통을 가지고 있습니다.

경기도: 이동 막걸리, 오산 막걸리 등이 유명하며, 쌀 막걸리가 특징입니다
강원도: 감자 막걸리, 옥수수 막걸리 등 지역 특산물을 활용합니다
경상도: 연천 막걸리, 밀양 막걸리 등이 있으며, 묵직한 바디감이 특징입니다
전라도: 전주 막걸리, 남원 막걸리 등이 유명하며, 부드러운 맛이 특징입니다
제주도: 귤 막걸리, 한라산 막걸리 등 제주 특산물을 활용합니다

각 지역의 기후와 재료가 막걸리의 맛에 큰 영향을 미칩니다.
""",
                "source": "농촌진흥청",
                "category": "지역",
                "metadata": {"keywords": ["막걸리", "지역", "경기도", "강원도", "경상도", "전라도", "제주도"]}
            },
            {
                "id": "doc_007",
                "title": "전통주와 건강",
                "content": """
전통주는 적당히 섭취하면 건강에 도움이 될 수 있습니다.

영양소: 막걸리는 단백질, 비타민 B군, 미네랄 등이 풍부합니다
소화: 유산균이 포함되어 있어 소화를 돕습니다
혈액순환: 적당한 알코올은 혈액순환을 돕습니다

하지만 과도한 섭취는 건강에 해롭습니다.
하루 1-2잔 이내로 섭취하는 것이 권장됩니다.
""",
                "source": "전통주갤러리",
                "category": "건강",
                "metadata": {"keywords": ["전통주", "건강", "막걸리", "영양소"]}
            },
            {
                "id": "doc_008",
                "title": "전통주 문화",
                "content": """
한국의 전통주는 단순한 술을 넘어 문화적 가치를 가집니다.

명절: 설날, 추석 등 명절에 전통주를 마시는 풍습이 있습니다
제사: 제사상에 전통주를 올리는 전통이 있습니다
사회: 어른께 술을 따르는 예절이 중요합니다

전통주는 한국인의 정서와 생활 양식을 반영하는 중요한 문화 유산입니다.
최근에는 전통주의 가치를 재조명하려는 움직임이 활발합니다.
""",
                "source": "농촌진흥청",
                "category": "문화",
                "metadata": {"keywords": ["전통주", "문화", "명절", "제사", "예절"]}
            }
        ]

        for doc in sample_docs:
            self.add_document(doc)

    def add_document(self, document: Dict):
        """
        문서 추가

        Args:
            document: 문서 딕셔너리
        """
        doc = RAGDocument(**document)
        self.documents.append(doc)

        # 카테고리 인덱싱
        self.document_index[doc.category].append(doc.id)

        # TF-IDF 벡터화 (간단 구현)
        self._index_document(doc)

        logger.info(f"문서 추가: {doc.title}")

    def _index_document(self, document: RAGDocument):
        """문서 인덱싱 (TF-IDF)"""
        # 텍스트 전처리
        text = document.title + " " + document.content
        words = self._tokenize(text)

        # 단어 빈도 계산
        word_freq = defaultdict(int)
        for word in words:
            word_freq[word] += 1
            self.vocabulary.add(word)

        # TF-IDF 벡터 계산 (간단 구현)
        vector = {}
        for word in self.vocabulary:
            tf = word_freq.get(word, 0)
            # IDF는 문서 수로 나누는 간단한 구현
            idf = len(self.documents) / (sum(1 for d in self.documents if word in d.title + " " + d.content) + 1)
            vector[word] = tf * idf

        self.document_vectors[document.id] = vector

    def _tokenize(self, text: str) -> List[str]:
        """텍스트 토큰화"""
        # 간단한 형태소 분석 (공백, 특수문자 기준)
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()

        # 불용어 제거
        stopwords = {'이', '가', '은', '는', '의', '를', '을', '에', '와', '과', '하다', '있다', '되다'}
        words = [word for word in words if word not in stopwords and len(word) > 1]

        return words

    def search(self, query: str, top_k: int = 5, category: Optional[str] = None) -> RAGSearchResponse:
        """
        문서 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 k개
            category: 카테고리 필터

        Returns:
            검색 결과
        """
        # 쿼리 벡터화
        query_words = self._tokenize(query)
        query_vector = defaultdict(int)
        for word in query_words:
            query_vector[word] += 1

        # 유사도 계산
        similarities = []
        for doc in self.documents:
            # 카테고리 필터링
            if category and doc.category != category:
                continue

            # 코사인 유사도 계산
            doc_vector = self.document_vectors.get(doc.id, {})
            similarity = self._cosine_similarity(query_vector, doc_vector)

            similarities.append({
                'id': doc.id,
                'title': doc.title,
                'content': doc.content[:200] + "...",
                'source': doc.source,
                'category': doc.category,
                'similarity': similarity
            })

        # 유사도 순 정렬
        similarities.sort(key=lambda x: x['similarity'], reverse=True)

        return RAGSearchResponse(
            query=query,
            results=similarities[:top_k],
            total=len(similarities)
        )

    def _cosine_similarity(self, vec1: Dict, vec2: Dict) -> float:
        """코사인 유사도 계산"""
        # 공통 키
        keys = set(vec1.keys()) | set(vec2.keys())

        if not keys:
            return 0.0

        # 내적
        dot_product = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in keys)

        # 노름
        norm1 = sum(vec1.get(k, 0) ** 2 for k in keys) ** 0.5
        norm2 = sum(vec2.get(k, 0) ** 2 for k in keys) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def get_documents_by_category(self, category: str) -> List[RAGDocument]:
        """
        카테고리별 문서 조회

        Args:
            category: 카테고리

        Returns:
            문서 리스트
        """
        doc_ids = self.document_index.get(category, [])
        return [doc for doc in self.documents if doc.id in doc_ids]

    def save_db(self):
        """DB 저장"""
        db_data = {
            'documents': [
                {
                    'id': doc.id,
                    'title': doc.title,
                    'content': doc.content,
                    'source': doc.source,
                    'category': doc.category,
                    'metadata': doc.metadata
                }
                for doc in self.documents
            ],
            'vocabulary': list(self.vocabulary),
            'document_vectors': self.document_vectors
        }

        with open(self.db_path / 'rag_db.json', 'w', encoding='utf-8') as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)

        logger.info(f"DB 저장 완료: {self.db_path / 'rag_db.json'}")

    def load_db(self):
        """DB 로드"""
        db_file = self.db_path / 'rag_db.json'

        if not db_file.exists():
            logger.warning(f"DB 파일 없음: {db_file}")
            return

        with open(db_file, 'r', encoding='utf-8') as f:
            db_data = json.load(f)

        # 문서 로드
        self.documents = []
        for doc_data in db_data['documents']:
            self.add_document(doc_data)

        # 어휘 로드
        self.vocabulary = set(db_data['vocabulary'])

        # 벡터 로드
        self.document_vectors = db_data['document_vectors']

        logger.info(f"DB 로드 완료: {len(self.documents)}개 문서")


def main():
    """메인 실행 함수"""
    rag = TraditionalAlcoholRAG()

    print("=== 전통주 RAG 시스템 테스트 ===\n")

    # 1. 문서 검색
    print("--- 1. 문서 검색 ---")
    queries = [
        "막걸리 역사",
        "막걸리 제조 방법",
        "막걸리와 음식 페어링",
        "지역별 막걸리",
        "전통주 보관"
    ]

    for query in queries:
        print(f"\n쿼리: {query}")
        results = rag.search(query, top_k=2)

        for i, result in enumerate(results.results, 1):
            print(f"  {i}. {result['title']} (유사도: {result['similarity']:.3f})")
            print(f"     카테고리: {result['category']}, 출처: {result['source']}")

    # 2. 카테고리별 문서 조회
    print("\n--- 2. 카테고리별 문서 조회 ---")
    categories = ["역사", "제조", "페어링", "지역"]

    for category in categories:
        docs = rag.get_documents_by_category(category)
        print(f"\n{category}: {len(docs)}개 문서")
        for doc in docs:
            print(f"  - {doc.title}")

    # 3. DB 저장/로드 테스트
    print("\n--- 3. DB 저장/로드 테스트 ---")
    rag.save_db()

    new_rag = TraditionalAlcoholRAG()
    new_rag.load_db()

    print(f"로드된 문서 수: {len(new_rag.documents)}")
    print(f"어휘 크기: {len(new_rag.vocabulary)}")


if __name__ == "__main__":
    main()
