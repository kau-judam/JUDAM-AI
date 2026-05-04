"""
고도화된 막걸리 추천 시스템
다중 소스 앙상블 + 취향 진화 트래킹 + 역추천
"""

import json
import logging
import math
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedMakgeolliRecommender:
    """고도화된 막걸리 추천 시스템"""

    def __init__(self, data_file: str = "data/processed/makgeolli_with_vectors.json"):
        self.data_file = Path(data_file)
        self.drinks = []
        self.load_data()

        # 사용자 취향 히스토리 (취향 진화 트래킹)
        self.user_taste_history = defaultdict(list)

        # 안주 매칭 데이터
        self.food_pairings = {
            '갈비찜': ['이동 생 쌀 막걸리', '오산막걸리', '연천 아주'],
            '치킨': ['얼떨결에', '오미자 생막걸리', '가야 프리미엄 막걸리'],
            '홍어무침': ['오산막걸리', '연천 아주', '미생 막걸리'],
            '오징어무침': ['오산막걸리', '연천 아주', '성포 생막걸리'],
            '삼겹살': ['우곡생주', '양지백주', '연천 율무 동동주'],
            '회': ['우곡생주', '양지백주', '연천 율무 동동주'],
            '족발': ['우곡생주', '양지백주', '연천 율무 동동주'],
            '떡볶이': ['오미자 생막걸리', '가야 프리미엄 막걸리', '오산막걸리'],
            '파전': ['오미자 생막걸리', '가야 프리미엄 막걸리', '기다림 16'],
            '김치찌개': ['이동 생 쌀 막걸리', '오산막걸리', '연천 아주']
        }

    def load_data(self):
        """데이터 로드"""
        if self.data_file.exists():
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.drinks = json.load(f)
            logger.info(f"데이터 로드 완료: {len(self.drinks)}개")
        else:
            logger.warning(f"데이터 파일 없음: {self.data_file}")

    def cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """코사인 유사도 계산"""
        axes = ['sweetness', 'body', 'carbonation', 'flavor', 'alcohol', 'acidity', 'aroma_intensity', 'finish']

        dot_product = sum(vec1[axis] * vec2[axis] for axis in axes)
        norm1 = math.sqrt(sum(vec1[axis] ** 2 for axis in axes))
        norm2 = math.sqrt(sum(vec2[axis] ** 2 for axis in axes))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def ingredient_similarity(self, ingredients1: str, ingredients2: str) -> float:
        """원재료 유사도 계산"""
        if not ingredients1 or not ingredients2:
            return 0.0

        # 문자열로 변환
        ing1_str = str(ingredients1) if not isinstance(ingredients1, str) else ingredients1
        ing2_str = str(ingredients2) if not isinstance(ingredients2, str) else ingredients2

        # 원재료 추출
        ing1 = set(ing1_str.replace(',', ' ').split())
        ing2 = set(ing2_str.replace(',', ' ').split())

        if not ing1 or not ing2:
            return 0.0

        # 자카드 유사도
        intersection = len(ing1 & ing2)
        union = len(ing1 | ing2)

        return intersection / union if union > 0 else 0.0

    def region_similarity(self, region1: str, region2: str) -> float:
        """지역 유사도 계산"""
        if not region1 or not region2:
            return 0.0

        # 같은 지역이면 1.0, 아니면 0.0
        return 1.0 if region1 == region2 else 0.0

    def multi_source_similarity(self, user_vector: Dict[str, float], drink: Dict, weights: Dict[str, float] = None) -> float:
        """
        다중 소스 앙상블 유사도 계산

        Args:
            user_vector: 사용자 맛 벡터
            drink: 막걸리 데이터
            weights: 가중치 (taste, ingredient, region)

        Returns:
            앙상블 유사도
        """
        if weights is None:
            weights = {
                'taste': 0.7,
                'ingredient': 0.2,
                'region': 0.1
            }

        # 맛 벡터 유사도
        taste_sim = self.cosine_similarity(user_vector, drink['taste_vector'])

        # 원재료 유사도
        ingredient_sim = self.ingredient_similarity(
            ' '.join([str(v) for v in user_vector.values()]),
            drink.get('ingredients', '')
        )

        # 지역 유사도
        region_sim = 0.0  # 사용자 지역 정보가 없으므로 0

        # 앙상블 유사도
        ensemble_sim = (
            weights['taste'] * taste_sim +
            weights['ingredient'] * ingredient_sim +
            weights['region'] * region_sim
        )

        return ensemble_sim

    def recommend(self, user_vector: Dict[str, float], top_k: int = 10, exclude_ids: List[str] = None, weights: Dict[str, float] = None) -> List[Dict]:
        """
        다중 소스 앙상블 추천

        Args:
            user_vector: 사용자 맛 벡터
            top_k: 추천할 상위 k개
            exclude_ids: 제외할 ID 리스트
            weights: 가중치

        Returns:
            추천 결과 리스트
        """
        if exclude_ids is None:
            exclude_ids = []

        # 유사도 계산
        recommendations = []
        for drink in self.drinks:
            if drink['id'] in exclude_ids:
                continue

            similarity = self.multi_source_similarity(user_vector, drink, weights)

            recommendations.append({
                'id': drink['id'],
                'name': drink['name'],
                'similarity': similarity,
                'abv': drink['abv'],
                'brewery': drink['brewery'],
                'region': drink['region'],
                'features': drink['features'],
                'ingredients': drink['ingredients'],
                'taste_vector': drink['taste_vector']
            })

        # 유사도 순으로 정렬
        recommendations.sort(key=lambda x: x['similarity'], reverse=True)

        # 상위 k개 반환
        return recommendations[:top_k]

    def recommend_by_food(self, food: str, top_k: int = 5) -> List[Dict]:
        """
        음식 기반 역추천

        Args:
            food: 음식 이름
            top_k: 추천할 상위 k개

        Returns:
            추천 결과 리스트
        """
        # 안주 매칭
        paired_drinks = self.food_pairings.get(food, [])

        # 매칭된 막걸리 찾기
        recommendations = []
        for drink_name in paired_drinks:
            for drink in self.drinks:
                if drink['name'] == drink_name:
                    recommendations.append({
                        'id': drink['id'],
                        'name': drink['name'],
                        'abv': drink['abv'],
                        'brewery': drink['brewery'],
                        'region': drink['region'],
                        'features': drink['features'],
                        'taste_vector': drink['taste_vector'],
                        'reason': f"{food}와 잘 어울립니다"
                    })
                    break

        return recommendations[:top_k]

    def update_user_taste(self, user_id: str, drink_id: str, rating: int, tags: List[str] = None):
        """
        사용자 취향 업데이트 (취향 진화 트래킹)

        Args:
            user_id: 사용자 ID
            drink_id: 막걸리 ID
            rating: 별점 (1~5)
            tags: 태그 리스트
        """
        # 막걸리 찾기
        drink = None
        for d in self.drinks:
            if d['id'] == drink_id:
                drink = d
                break

        if not drink:
            logger.warning(f"막걸리 찾기 실패: {drink_id}")
            return

        # 취향 히스토리에 추가
        self.user_taste_history[user_id].append({
            'drink_id': drink_id,
            'drink_name': drink['name'],
            'rating': rating,
            'tags': tags or [],
            'taste_vector': drink['taste_vector'],
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"사용자 취향 업데이트: {user_id} - {drink['name']} ({rating}점)")

    def get_evolved_taste_vector(self, user_id: str) -> Dict[str, float]:
        """
        진화된 사용자 맛 벡터 계산

        Args:
            user_id: 사용자 ID

        Returns:
            진화된 맛 벡터
        """
        history = self.user_taste_history.get(user_id, [])

        if not history:
            # 히스토리가 없으면 기본 벡터 반환
            return {
                'sweetness': 5.0,
                'body': 5.0,
                'carbonation': 5.0,
                'flavor': 5.0,
                'alcohol': 5.0,
                'acidity': 5.0,
                'aroma_intensity': 5.0,
                'finish': 5.0
            }

        # 평가 수에 따른 가중치 계산
        num_ratings = len(history)

        if num_ratings == 1:
            taste_weight = 0.9
            rating_weight = 0.1
        elif num_ratings <= 10:
            taste_weight = 0.7
            rating_weight = 0.3
        elif num_ratings <= 50:
            taste_weight = 0.5
            rating_weight = 0.5
        else:
            taste_weight = 0.2
            rating_weight = 0.8

        # 기본 맛 벡터 (초기값)
        base_vector = {
            'sweetness': 5.0,
            'body': 5.0,
            'carbonation': 5.0,
            'flavor': 5.0,
            'alcohol': 5.0,
            'acidity': 5.0,
            'aroma_intensity': 5.0,
            'finish': 5.0
        }

        # 평가 기반 벡터 계산
        rating_vector = {axis: 0.0 for axis in base_vector.keys()}
        total_weight = 0.0

        for record in history:
            rating = record['rating']
            taste_vector = record['taste_vector']

            # 별점에 따른 가중치
            if rating == 5:
                weight = 1.0
            elif rating == 4:
                weight = 0.5
            elif rating == 3:
                weight = 0.0
            elif rating == 2:
                weight = -0.5
            else:  # rating == 1
                weight = -1.0

            # 벡터 업데이트
            for axis in base_vector.keys():
                rating_vector[axis] += taste_vector[axis] * weight

            total_weight += abs(weight)

        # 정규화
        if total_weight > 0:
            for axis in base_vector.keys():
                rating_vector[axis] /= total_weight

        # 앙상블
        evolved_vector = {}
        for axis in base_vector.keys():
            evolved_vector[axis] = round(
                base_vector[axis] * taste_weight + rating_vector[axis] * rating_weight,
                1
            )

        return evolved_vector

    def recommend_with_evolution(self, user_id: str, top_k: int = 10) -> List[Dict]:
        """
        취향 진화 트래킹 기반 추천

        Args:
            user_id: 사용자 ID
            top_k: 추천할 상위 k개

        Returns:
            추천 결과 리스트
        """
        # 진화된 맛 벡터 계산
        evolved_vector = self.get_evolved_taste_vector(user_id)

        # 추천
        recommendations = self.recommend(evolved_vector, top_k)

        # 취향 진화 정보 추가
        for rec in recommendations:
            rec['evolved_taste'] = evolved_vector

        return recommendations

    def get_sample_user_vectors(self) -> List[Dict[str, Dict[str, float]]]:
        """샘플 사용자 맛 벡터 반환"""
        return [
            {
                'name': '단맛 선호',
                'vector': {
                    'sweetness': 8.0,
                    'body': 5.0,
                    'carbonation': 5.0,
                    'flavor': 6.0,
                    'alcohol': 5.0,
                    'acidity': 4.0,
                    'aroma_intensity': 5.0,
                    'finish': 5.0
                }
            },
            {
                'name': '산미 선호',
                'vector': {
                    'sweetness': 4.0,
                    'body': 5.0,
                    'carbonation': 6.0,
                    'flavor': 5.0,
                    'alcohol': 5.0,
                    'acidity': 8.0,
                    'aroma_intensity': 5.0,
                    'finish': 5.0
                }
            },
            {
                'name': '바디감 선호',
                'vector': {
                    'sweetness': 5.0,
                    'body': 8.0,
                    'carbonation': 4.0,
                    'flavor': 6.0,
                    'alcohol': 6.0,
                    'acidity': 5.0,
                    'aroma_intensity': 5.0,
                    'finish': 6.0
                }
            },
            {
                'name': '탄산 선호',
                'vector': {
                    'sweetness': 5.0,
                    'body': 4.0,
                    'carbonation': 8.0,
                    'flavor': 5.0,
                    'alcohol': 5.0,
                    'acidity': 6.0,
                    'aroma_intensity': 5.0,
                    'finish': 5.0
                }
            },
            {
                'name': '밸런스형',
                'vector': {
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
        ]


def main():
    """메인 실행 함수"""
    recommender = AdvancedMakgeolliRecommender()

    print("=== 고도화된 막걸리 추천 시스템 테스트 ===\n")

    # 1. 다중 소스 앙상블 추천
    print("--- 1. 다중 소스 앙상블 추천 ---")
    sample_users = recommender.get_sample_user_vectors()

    for user in sample_users[:2]:  # 2개만 테스트
        print(f"\n{user['name']}")
        print(f"사용자 맛 벡터: {user['vector']}")

        recommendations = recommender.recommend(user['vector'], top_k=3)

        print("추천 결과 (상위 3개):")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec['name']} (유사도: {rec['similarity']:.3f})")
            print(f"   도수: {rec['abv']}%, 양조장: {rec['brewery']}")

    # 2. 음식 기반 역추천
    print("\n--- 2. 음식 기반 역추천 ---")
    foods = ['갈비찜', '치킨', '홍어무침']

    for food in foods:
        print(f"\n{food}와 어울리는 막걸리:")
        recommendations = recommender.recommend_by_food(food, top_k=3)

        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec['name']} - {rec['reason']}")

    # 3. 취향 진화 트래킹
    print("\n--- 3. 취향 진화 트래킹 ---")

    # 사용자 ID 생성
    user_id = "test_user_1"

    # 초기 맛 벡터
    initial_vector = recommender.get_evolved_taste_vector(user_id)
    print(f"초기 맛 벡터: {initial_vector}")

    # 평가 추가
    recommender.update_user_taste(user_id, "makgeolli_0", 5, ["달콤", "산미"])
    recommender.update_user_taste(user_id, "makgeolli_1", 4, ["바디감"])
    recommender.update_user_taste(user_id, "makgeolli_2", 3, ["탄산"])

    # 진화된 맛 벡터
    evolved_vector = recommender.get_evolved_taste_vector(user_id)
    print(f"진화된 맛 벡터: {evolved_vector}")

    # 진화된 맛 벡터 기반 추천
    recommendations = recommender.recommend_with_evolution(user_id, top_k=3)

    print("\n진화된 맛 벡터 기반 추천:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['name']} (유사도: {rec['similarity']:.3f})")


if __name__ == "__main__":
    main()
