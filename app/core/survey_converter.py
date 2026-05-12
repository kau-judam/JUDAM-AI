"""
술BTI 설문 → 맛 벡터 변환기
25문항 설문 응답을 8축 맛 벡터로 변환하는 모듈
"""

import logging
from typing import Dict, List
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SurveyResponse(BaseModel):
    """술BTI 25문항 설문 응답 모델"""

    # q1~q3: 서열척도 (1~5)
    q1: int = Field(..., ge=1, le=5, description="전통주 경험 수준 (1~5)")
    q2: int = Field(..., ge=1, le=5, description="선호 도수 수준 (1~5)")
    q3: int = Field(..., ge=1, le=5, description="선호 바디감/색상 수준 (1~5)")

    # q4~q22: 등간척도 Likert (1~7)
    q4: int = Field(..., ge=1, le=7, description="단맛 선호도 (1~7)")
    q5: int = Field(..., ge=1, le=7, description="신맛 선호도 (1~7)")
    q6: int = Field(..., ge=1, le=7, description="청량감 선호도 (1~7)")
    q7: int = Field(..., ge=1, le=7, description="과일 향 선호도 (1~7)")
    q8: int = Field(..., ge=1, le=7, description="여운 선호도 (1~7)")
    q9: int = Field(..., ge=1, le=7, description="풍미 복잡성 선호도 (1~7)")
    q10: int = Field(..., ge=1, le=7, description="바디감 선호도 (1~7)")
    q11: int = Field(..., ge=1, le=7, description="맛의 농도 선호도 (1~7)")
    q12: int = Field(..., ge=1, le=7, description="도수 내성 (1~7)")
    q13: int = Field(..., ge=1, le=7, description="알콜 감지 선호도 (1~7)")
    q14: int = Field(..., ge=1, le=7, description="탄산감 선호도 (1~7)")
    q15: int = Field(..., ge=1, le=7, description="향기 강도 선호도 (1~7)")
    q16: int = Field(..., ge=1, le=7, description="꽃향 선호도 (1~7)")
    q17: int = Field(..., ge=1, le=7, description="허브향 선호도 (1~7)")
    q18: int = Field(..., ge=1, le=7, description="과일향 선호도 (1~7)")
    q19: int = Field(..., ge=1, le=7, description="신선한 향 선호도 (1~7)")
    q20: int = Field(..., ge=1, le=7, description="구수한 향 선호도 (1~7)")
    q21: int = Field(..., ge=1, le=7, description="알콜 향 선호도 (1~7)")
    q22: int = Field(..., ge=1, le=7, description="전반적인 맛 강도 선호도 (1~7)")

    # q23: 명목척도 (1~5) - 선호 과일
    q23: int = Field(..., ge=1, le=5, description="선호 과일 (1~5)")

    # q24: 명목척도 복수선택 - 음식 페어링
    q24: List[int] = Field(..., description="음식 페어링 선호 (복수선택)")

    # q25: 명목척도 복수선택 - 관심 향
    q25: List[int] = Field(..., description="관심 향 (복수선택)")


class SurveyToVectorConverter:
    """25문항 설문 응답 → 8축 맛 벡터 변환기"""

    def __init__(self):
        # 과일별 맛 벡터 매핑 (q23)
        self.fruit_taste_map = {
            1: {'citrus': 8.0},      # 감귤류
            2: {'berry': 8.0},       # 베리류
            3: {'citrus': 7.0},      # 사과
            4: {'berry': 8.0},       # 포도
            5: {'tropical': 8.0}    # 망고
        }

        # 음식 페어링 매핑 (q24)
        self.food_pairing_map = {
            1: 'meat',      # 고기 요리
            2: 'seafood',   # 해산물
            3: 'spicy',     # 매운 음식
            4: 'dessert',   # 디저트
            5: 'cheese'     # 치즈
        }

        # 향기 매핑 (q25)
        self.aroma_map = {
            1: 'other_fruit',  # 기타 과일
            2: 'citrus',       # 감귤류
            3: 'flower',       # 꽃향
            4: 'herb',         # 허브
            5: 'rice'          # 쌀향
        }

    def convert(self, survey: SurveyResponse) -> Dict[str, float]:
        """
        25문항 설문 응답을 8축 맛 벡터로 변환

        Args:
            survey: 25문항 설문 응답

        Returns:
            8축 맛 벡터 딕셔너리
        """
        # q1~q3: 서열척도 처리
        experience_level = self._get_experience_level(survey.q1)
        alcohol_base = self._get_alcohol_base(survey.q2)
        body_base = self._get_body_base(survey.q3)

        # q4~q22: 등간척도 Likert 기반 8축 계산
        sweetness = self._calculate_sweetness(
            survey.q4, survey.q5, survey.q6, survey.q7, survey.q8, survey.q9
        )
        body = self._calculate_body(
            survey.q10, survey.q11, survey.q13, survey.q6
        )
        carbonation = self._calculate_carbonation(
            survey.q14, survey.q15, survey.q7
        )
        flavor = self._calculate_flavor(
            survey.q17, survey.q18, survey.q20, survey.q9
        )
        alcohol = self._calculate_alcohol(
            survey.q21, survey.q12, survey.q13, alcohol_base
        )
        acidity = self._calculate_acidity(
            survey.q5, survey.q14, survey.q19, survey.q18
        )
        aroma_intensity = self._calculate_aroma_intensity(
            survey.q15, survey.q16, survey.q17, survey.q18
        )
        finish = self._calculate_finish(
            survey.q8, survey.q16, survey.q14
        )

        # q23: 과일 선호 반영
        fruit_taste = self.fruit_taste_map.get(survey.q23, {})
        for key, value in fruit_taste.items():
            if key == 'citrus':
                aroma_intensity = min(10, aroma_intensity + value * 0.1)
            elif key == 'berry':
                flavor = min(10, flavor + value * 0.1)
            elif key == 'tropical':
                sweetness = min(10, sweetness + value * 0.1)

        # q24: 음식 페어링 저장
        food_pairing = [self.food_pairing_map.get(f, 'unknown') for f in survey.q24]

        # q25: 향기 선호 반영
        for aroma_code in survey.q25:
            aroma = self.aroma_map.get(aroma_code)
            if aroma == 'other_fruit':
                flavor = min(10, flavor + 0.7)
            elif aroma == 'citrus':
                aroma_intensity = min(10, aroma_intensity + 0.7)
            elif aroma == 'flower':
                aroma_intensity = min(10, aroma_intensity + 0.7)
            elif aroma == 'herb':
                flavor = min(10, flavor + 0.7)
            elif aroma == 'rice':
                body = min(10, body + 0.7)

        # 결과 조합
        vector = {
            'sweetness': round(sweetness, 2),
            'body': round(body, 2),
            'carbonation': round(carbonation, 2),
            'flavor': round(flavor, 2),
            'alcohol': round(alcohol, 2),
            'acidity': round(acidity, 2),
            'aroma_intensity': round(aroma_intensity, 2),
            'finish': round(finish, 2),
            'food_pairing': food_pairing
        }

        logger.info(f"25문항 설문 응답 → 맛 벡터 변환 완료: {vector}")

        return vector

    def _get_experience_level(self, q1: int) -> str:
        """전통주 경험 수준 반환"""
        if q1 <= 2:
            return 'beginner'
        elif q1 == 3:
            return 'intermediate'
        else:
            return 'expert'

    def _get_alcohol_base(self, q2: int) -> float:
        """도수 초기값 반환"""
        mapping = {1: 2.0, 2: 4.0, 3: 6.0, 4: 8.0, 5: 10.0}
        return mapping.get(q2, 5.0)

    def _get_body_base(self, q3: int) -> float:
        """바디감/색상 초기값 반환"""
        mapping = {1: 1.0, 2: 3.0, 3: 5.0, 4: 7.0, 5: 9.0}
        return mapping.get(q3, 5.0)

    def _calculate_sweetness(self, q4: int, q5: int, q6: int, q7: int, q8: int, q9: int) -> float:
        """단맛 계산"""
        return (q4 * 0.30 + (8 - q5) * 0.20 + q6 * 0.10 + q7 * 0.15 + q8 * 0.15 + q9 * 0.10) / 7 * 10

    def _calculate_body(self, q10: int, q11: int, q13: int, q6: int) -> float:
        """바디감 계산"""
        return (q10 * 0.35 + q11 * 0.25 + q13 * 0.25 + (8 - q6) * 0.15) / 7 * 10

    def _calculate_carbonation(self, q14: int, q15: int, q7: int) -> float:
        """탄산감 계산"""
        return (q14 * 0.40 + (8 - q15) * 0.35 + q7 * 0.25) / 7 * 10

    def _calculate_flavor(self, q17: int, q18: int, q20: int, q9: int) -> float:
        """풍미 계산"""
        return ((8 - q17) * 0.20 + q18 * 0.30 + (8 - q20) * 0.25 + q9 * 0.25) / 7 * 10

    def _calculate_alcohol(self, q21: int, q12: int, q13: int, base: float) -> float:
        """도수 계산"""
        calculated = ((8 - q21) * 0.40 + q12 * 0.35 + q13 * 0.25) / 7 * 10
        # 기본값과 계산값 가중 평균
        return (calculated * 0.7 + base * 0.3)

    def _calculate_acidity(self, q5: int, q14: int, q19: int, q18: int) -> float:
        """산미 계산"""
        return ((8 - q5) * 0.30 + q14 * 0.20 + q19 * 0.30 + q18 * 0.20) / 7 * 10

    def _calculate_aroma_intensity(self, q15: int, q16: int, q17: int, q18: int) -> float:
        """향기 강도 계산"""
        return ((8 - q15) * 0.30 + q16 * 0.30 + q17 * 0.20 + q18 * 0.20) / 7 * 10

    def _calculate_finish(self, q8: int, q16: int, q14: int) -> float:
        """여운 계산"""
        return (q8 * 0.35 + q16 * 0.35 + (8 - q14) * 0.30) / 7 * 10


def main():
    """메인 실행 함수"""
    converter = SurveyToVectorConverter()

    print("=== 25문항 술BTI 설문 → 맛 벡터 변환 테스트 ===\n")

    # 테스트 케이스 1
    print("--- 테스트 케이스 1 ---")
    survey1 = SurveyResponse(
        q1=1, q2=1, q3=3,
        q4=7, q5=2, q6=7, q7=6, q8=6, q9=5,
        q10=2, q11=2, q12=1, q13=2,
        q14=7, q15=3, q16=4, q17=3, q18=6, q19=3, q20=3, q21=7, q22=3,
        q23=4, q24=[1, 4], q25=[1, 2]
    )
    print(f"설문 응답: {survey1.model_dump()}")
    vector1 = converter.convert(survey1)
    print(f"맛 벡터: {vector1}\n")

    # 테스트 케이스 2
    print("--- 테스트 케이스 2 ---")
    survey2 = SurveyResponse(
        q1=5, q2=4, q3=5,
        q4=2, q5=6, q6=3, q7=2, q8=3, q9=4,
        q10=6, q11=6, q12=6, q13=6,
        q14=2, q15=5, q16=5, q17=6, q18=3, q19=5, q20=6, q21=2, q22=6,
        q23=2, q24=[2, 3], q25=[4, 5]
    )
    print(f"설문 응답: {survey2.model_dump()}")
    vector2 = converter.convert(survey2)
    print(f"맛 벡터: {vector2}\n")


if __name__ == "__main__":
    main()
