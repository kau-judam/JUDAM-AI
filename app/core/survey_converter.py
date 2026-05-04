"""
술BTI 설문 → 맛 벡터 변환기
설문 응답을 맛 벡터로 변환하는 모듈
"""

import logging
from typing import Dict, List
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SurveyResponse(BaseModel):
    """술BTI 설문 응답 모델"""

    # 공개용 5개 축
    sweetness: int = Field(..., ge=0, le=10, description="단맛 선호도 (0~10)")
    body: int = Field(..., ge=0, le=10, description="바디감 선호도 (0~10)")
    carbonation: int = Field(..., ge=0, le=10, description="탄산 선호도 (0~10)")
    flavor: int = Field(..., ge=0, le=10, description="풍미 선호도 (0~10)")
    alcohol: int = Field(..., ge=0, le=10, description="도수 선호도 (0~10)")

    # 추가 정보 (선택)
    preferred_ingredients: List[str] = Field(default_factory=list, description="선호하는 재료")
    disliked_ingredients: List[str] = Field(default_factory=list, description="싫어하는 재료")
    preferred_region: str = Field(default="", description="선호하는 지역")


class SurveyToVectorConverter:
    """설문 응답 → 맛 벡터 변환기"""

    def __init__(self):
        # 기본 맛 벡터 (8개 축)
        self.base_vector = {
            'sweetness': 5.0,
            'body': 5.0,
            'carbonation': 5.0,
            'flavor': 5.0,
            'alcohol': 5.0,
            'acidity': 5.0,
            'aroma_intensity': 5.0,
            'finish': 5.0
        }

        # 재료 기반 맛 조정
        self.ingredient_taste_adjustment = {
            '쌀': {'sweetness': 0, 'body': 0, 'carbonation': 0, 'flavor': 0, 'alcohol': 0, 'acidity': 0, 'aroma_intensity': 0, 'finish': 0},
            '밀': {'sweetness': -1, 'body': 2, 'carbonation': 0, 'flavor': 1, 'alcohol': 0, 'acidity': 0, 'aroma_intensity': 0, 'finish': 0},
            '찹쌀': {'sweetness': 2, 'body': 2, 'carbonation': 0, 'flavor': 2, 'alcohol': 0, 'acidity': 0, 'aroma_intensity': 0, 'finish': 0},
            '유자': {'sweetness': 2, 'body': -1, 'carbonation': 0, 'flavor': 2, 'alcohol': 0, 'acidity': 2, 'aroma_intensity': 1, 'finish': 0},
            '오미자': {'sweetness': 2, 'body': -1, 'carbonation': 0, 'flavor': 2, 'alcohol': 0, 'acidity': 2, 'aroma_intensity': 1, 'finish': 0},
            '복분자': {'sweetness': 2, 'body': -1, 'carbonation': 0, 'flavor': 2, 'alcohol': 0, 'acidity': 2, 'aroma_intensity': 1, 'finish': 0},
            '매실': {'sweetness': 2, 'body': -1, 'carbonation': 0, 'flavor': 2, 'alcohol': 0, 'acidity': 2, 'aroma_intensity': 1, 'finish': 0},
            '율무': {'sweetness': -1, 'body': 0, 'carbonation': 0, 'flavor': 0, 'alcohol': 0, 'acidity': 0, 'aroma_intensity': 0, 'finish': 0},
            '누룩': {'sweetness': 0, 'body': 1, 'carbonation': 0, 'flavor': 1, 'alcohol': 0, 'acidity': 0, 'aroma_intensity': 0, 'finish': 0},
            '효모': {'sweetness': 0, 'body': 0, 'carbonation': 0, 'flavor': 0, 'alcohol': 0, 'acidity': 0, 'aroma_intensity': 0, 'finish': 0},
            '젖산': {'sweetness': 0, 'body': 0, 'carbonation': 0, 'flavor': 0, 'alcohol': 0, 'acidity': 2, 'aroma_intensity': 0, 'finish': 0}
        }

    def convert(self, survey: SurveyResponse) -> Dict[str, float]:
        """
        설문 응답을 맛 벡터로 변환

        Args:
            survey: 설문 응답

        Returns:
            맛 벡터 딕셔너리
        """
        # 기본 맛 벡터 복사
        vector = self.base_vector.copy()

        # 설문 응답 반영
        vector['sweetness'] = float(survey.sweetness)
        vector['body'] = float(survey.body)
        vector['carbonation'] = float(survey.carbonation)
        vector['flavor'] = float(survey.flavor)
        vector['alcohol'] = float(survey.alcohol)

        # 재료 기반 조정
        for ingredient in survey.preferred_ingredients:
            if ingredient in self.ingredient_taste_adjustment:
                adjustment = self.ingredient_taste_adjustment[ingredient]
                for axis, value in adjustment.items():
                    vector[axis] = max(0, min(10, vector[axis] + value))

        for ingredient in survey.disliked_ingredients:
            if ingredient in self.ingredient_taste_adjustment:
                adjustment = self.ingredient_taste_adjustment[ingredient]
                for axis, value in adjustment.items():
                    vector[axis] = max(0, min(10, vector[axis] - value))

        # 값 범위 확인
        for axis in vector:
            vector[axis] = max(0, min(10, vector[axis]))

        logger.info(f"설문 응답 → 맛 벡터 변환 완료: {vector}")

        return vector

    def get_sample_surveys(self) -> List[SurveyResponse]:
        """샘플 설문 응답 반환"""
        return [
            SurveyResponse(
                sweetness=8,
                body=5,
                carbonation=5,
                flavor=6,
                alcohol=5,
                preferred_ingredients=['유자', '오미자'],
                disliked_ingredients=['밀'],
                preferred_region='경상남도'
            ),
            SurveyResponse(
                sweetness=4,
                body=5,
                carbonation=6,
                flavor=5,
                alcohol=5,
                preferred_ingredients=['쌀'],
                disliked_ingredients=['밀'],
                preferred_region='경기도'
            ),
            SurveyResponse(
                sweetness=5,
                body=8,
                carbonation=4,
                flavor=6,
                alcohol=6,
                preferred_ingredients=['찹쌀'],
                disliked_ingredients=['유자'],
                preferred_region='경상북도'
            ),
            SurveyResponse(
                sweetness=5,
                body=4,
                carbonation=8,
                flavor=5,
                alcohol=5,
                preferred_ingredients=['쌀'],
                disliked_ingredients=['밀'],
                preferred_region='강원도'
            ),
            SurveyResponse(
                sweetness=5,
                body=5,
                carbonation=5,
                flavor=5,
                alcohol=5,
                preferred_ingredients=[],
                disliked_ingredients=[],
                preferred_region=''
            )
        ]


def main():
    """메인 실행 함수"""
    converter = SurveyToVectorConverter()

    print("=== 술BTI 설문 → 맛 벡터 변환 테스트 ===\n")

    # 샘플 설문 응답
    sample_surveys = converter.get_sample_surveys()

    for i, survey in enumerate(sample_surveys, 1):
        print(f"--- 샘플 {i} ---")
        print(f"설문 응답: {survey.model_dump()}")

        # 맛 벡터 변환
        vector = converter.convert(survey)

        print(f"맛 벡터: {vector}")
        print()


if __name__ == "__main__":
    main()
