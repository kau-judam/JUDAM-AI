"""
술BTI 설문 → 맛 벡터 변환기
25문항 설문 응답을 8축 맛 벡터로 변환하는 모듈
"""

import logging
from typing import Dict, List
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BTI_TYPE_MAPPING = {
    "SHFC": {"name": "꿀단지에 빠진 인절미", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["꿀 막걸리", "밤 막걸리", "탄산 생막걸리"]},
    "SHFU": {"name": "탄산 톡톡 딸기 요거트", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["딸기 탄산막걸리", "복숭아 생막걸리", "유자 탁주"]},
    "SHMC": {"name": "쫀득쫀득 꿀 찹쌀떡", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["찹쌀탁주", "원주 막걸리", "고구마 막걸리"]},
    "SHMU": {"name": "포근포근 꽃복숭아", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["망고 막걸리", "블루베리 탁주", "샤인머스캣 막걸리"]},
    "SLFC": {"name": "청량함 가득 사과 푸딩", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["저도수 생막걸리", "쌀 막걸리", "캔 막걸리"]},
    "SLFU": {"name": "팝핑 과일 에이드", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["자몽 막걸리", "레몬 탁주", "오미자 탄산막걸리"]},
    "SLMC": {"name": "햇살 머금은 식혜", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["맑은 탁주", "단술", "저도수 쌀막걸리"]},
    "SLMU": {"name": "산들바람 머금은 화전", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["꽃잎 막걸리", "허브 탁주", "사과 막걸리"]},
    "DHFC": {"name": "바삭하게 터지는 현미 누룽지", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["고도수 생막걸리", "드라이한 탁주", "호밀 막걸리"]},
    "DHFU": {"name": "반전매력 고추냉이", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["오미자 탄산막걸리", "생강 탁주", "쑥 막걸리"]},
    "DHMC": {"name": "묵묵한 바위 속 숭늉", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["무감미료 탁주", "고도수 원주", "옥수수 막걸리"]},
    "DHMU": {"name": "안개 낀 숲속의 황금사과", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["산미 특화 막걸리", "약재 향 탁주", "드라이 과일막걸리"]},
    "DLFC": {"name": "청량한 대나무 숲의 차", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["가벼운 드라이 막걸리", "탄산 약주", "쌀 생막걸리"]},
    "DLFU": {"name": "차가운 도시의 샹그리아", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["드라이 유자막걸리", "진저 탁주", "탄산 베리막걸리"]},
    "DLMC": {"name": "대숲에 앉은 맑은 백설기", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["정통 드라이 탁주", "맑은 막걸리", "가벼운 누룩주"]},
    "DLMU": {"name": "빗소리 들리는 다실의 꽃차", "tags": ["#부드러운단맛", "#화사한과일향"], "drinks": ["산미 있는 가벼운 탁주", "허브 드라이막걸리", "차 콜라보 막걸리"]},
}

_ABV_LABEL = {1: "저도수(3도 이하)", 2: "약한 도수(4~6도)", 3: "중간 도수(7~9도)", 4: "높은 도수(10~13도)", 5: "고도수(14도 이상)"}
_BODY_LABEL = {1: "매우 가벼움", 2: "가벼움", 3: "보통", 4: "묵직함", 5: "매우 묵직함"}
_FRUIT_LABEL = {1: "감귤류", 2: "베리류", 3: "사과", 4: "포도", 5: "망고"}
_FOOD_LABEL = {1: "고기", 2: "해산물", 3: "매운음식", 4: "디저트", 5: "치즈"}
_AROMA_LABEL = {1: "과일향", 2: "감귤향", 3: "꽃향", 4: "허브향", 5: "쌀향"}

_DESCRIPTOR_CONJ = {
    "달콤한": "달콤하고", "드라이한": "드라이하고", "청량한": "청량하고",
    "부드러운": "부드럽고", "묵직한": "묵직하고", "가벼운": "가볍고",
    "향이 풍부한": "향이 풍부하고", "산미 있는": "산미 있고", "여운이 긴": "여운이 길고",
}


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

        # BTI 코드 판정 (기준 5.0 이진분류)
        bti_code = (
            ('S' if sweetness >= 5.0 else 'D') +
            ('H' if body >= 5.0 else 'L') +
            ('F' if carbonation >= 5.0 else 'M') +
            ('U' if flavor >= 5.0 else 'C')
        )
        character_name = BTI_TYPE_MAPPING.get(bti_code, {}).get('name', '')

        # 경험 수준
        if survey.q1 <= 2:
            experience_level = "입문자"
        elif survey.q1 == 3:
            experience_level = "중급자"
        else:
            experience_level = "전문가"

        # 선호 한글 매핑
        preferred_abv = _ABV_LABEL.get(survey.q2, '')
        preferred_body = _BODY_LABEL.get(survey.q3, '')
        preferred_fruit = _FRUIT_LABEL.get(survey.q23, '')
        preferred_food_pairing = [_FOOD_LABEL[f] for f in survey.q24 if f in _FOOD_LABEL]
        preferred_aroma = [_AROMA_LABEL[a] for a in survey.q25 if a in _AROMA_LABEL]

        # 맛 프로필 요약
        scored: List[tuple] = []
        if sweetness >= 6:
            scored.append(("달콤한", sweetness))
        elif sweetness <= 4:
            scored.append(("드라이한", 10 - sweetness))
        if carbonation >= 6:
            scored.append(("청량한", carbonation))
        elif carbonation <= 4:
            scored.append(("부드러운", 10 - carbonation))
        if body >= 6:
            scored.append(("묵직한", body))
        elif body <= 4:
            scored.append(("가벼운", 10 - body))
        if aroma_intensity >= 6:
            scored.append(("향이 풍부한", aroma_intensity))
        if acidity >= 6:
            scored.append(("산미 있는", acidity))
        if finish >= 6:
            scored.append(("여운이 긴", finish))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = [d[0] for d in scored[:3]]
        if not top:
            taste_profile_summary = "균형 잡힌 취향"
        elif len(top) == 1:
            taste_profile_summary = f"{top[0]} 취향"
        elif len(top) == 2:
            taste_profile_summary = f"{_DESCRIPTOR_CONJ.get(top[0], top[0])} {top[1]} 취향"
        else:
            taste_profile_summary = f"{_DESCRIPTOR_CONJ.get(top[0], top[0])} {_DESCRIPTOR_CONJ.get(top[1], top[1])} {top[2]} 취향"

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
            'food_pairing': food_pairing,
            'bti_code': bti_code,
            'character_name': character_name,
            'experience_level': experience_level,
            'preferred_abv': preferred_abv,
            'preferred_body': preferred_body,
            'preferred_fruit': preferred_fruit,
            'preferred_food_pairing': preferred_food_pairing,
            'preferred_aroma': preferred_aroma,
            'taste_profile_summary': taste_profile_summary,
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
