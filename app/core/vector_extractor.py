"""
고도화된 맛 벡터 추출기
향 노트 차원 추가 + 벡터 세분화 + NaN 처리
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedTasteVectorExtractor:
    """고도화된 맛 벡터 추출기"""

    def __init__(self):
        # 기본 맛 키워드 사전 (세분화)
        self.taste_keywords = {
            'sweetness': {
                'very_high': ['매우 달콤', '꿀처럼', '시럽', '과당', '올리고당', '물엿', '달콤한'],
                'high': ['달콤', '단맛', '당도', '과일', '꿀', '자몽', '유자', '복분자', '매실', '사과', '오미자'],
                'medium': ['약간 달콤', '적당한 단맛', '보통'],
                'low': ['드라이', '쓴맛', '단맛 없음', '달지 않음'],
                'very_low': ['신맛', '새콤', '시큼', '산미']
            },
            'body': {
                'very_high': ['매우 묵직', '농밀', '탁한', '걸쭉한', '진하다'],
                'high': ['묵직', '걸쭉', '진한', '농밀', '바디감', '무게감', '탁한'],
                'medium': ['적당', '보통', '중간'],
                'low': ['가볍', '깔끔', '맑은', '물처럼', '가벼운'],
                'very_low': ['청량', '가벼운', '맑은']
            },
            'carbonation': {
                'very_high': ['강한 탄산', '스파클링', '거품이 많은', '탄산감이 강한'],
                'high': ['탄산', '스파클링', '청량감', '거품', '거품이 많은', '탄산감', '시원'],
                'medium': ['약한 탄산', '적당한 탄산', '보통'],
                'low': ['탄산 없음', '무탄산', '부드러운', '평온'],
                'very_low': ['부드러운', '평온']
            },
            'flavor': {
                'very_high': ['풍미가 풍부', '향기가 풍부', '복합적인 맛', '다양한 맛'],
                'high': ['풍미', '향기', '과일향', '허브', '꽃향', '바닐라', '레몬', '라임', '유자향', '오미자향', '복분자향'],
                'medium': ['보통', '적당'],
                'low': ['전통적', '누룩향', '쌀향', '밋밋', '단조로운'],
                'very_low': ['밋밋', '단조로운']
            },
            'acidity': {
                'very_high': ['매우 신맛', '강한 산미', '새콤달콤', '시큼한'],
                'high': ['신맛', '산미', '새콤', '시큼', '유자', '오미자', '매실', '레몬', '라임'],
                'medium': ['약간 신맛', '적당한 산미', '보통'],
                'low': ['산미 없음', '신맛 없음', '부드러운'],
                'very_low': ['부드러운', '산미 없음']
            },
            'aroma_intensity': {
                'very_high': ['향이 매우 강한', '향이 진한', '향기가 풍부한', '향이 좋은'],
                'high': ['향이 강한', '향이 진한', '향기가 풍부한', '향이 좋은', '은은한 향'],
                'medium': ['보통', '적당'],
                'low': ['향이 없는', '향이 약한', '무취'],
                'very_low': ['향이 없는', '무취']
            },
            'finish': {
                'very_high': ['매우 긴 여운', '깊은 여운', '뒷맛이 길다'],
                'high': ['여운', '깊은', '긴 여운', '뒷맛', '여운이 길다', '뒷맛이 좋다'],
                'medium': ['보통', '적당'],
                'low': ['여운 없음', '뒷맛 없음', '깔끔'],
                'very_low': ['여운 없음', '뒷맛 없음', '깔끔']
            }
        }

        # 향 노트 키워드 사전
        self.note_keywords = {
            'fruit_notes': {
                'citrus': ['유자', '레몬', '라임', '귤', '오렌지', '감귤', '한라봉', '천혜향'],
                'berry': ['복분자', '매실', '오미자', '산딸기', '블루베리', '딸기', '라즈베리'],
                'stone_fruit': ['복숭아', '자두', '살구', '체리'],
                'apple_pear': ['사과', '배', '모과'],
                'tropical': ['망고', '파인애플', '바나나', '코코넛'],
                'other_fruit': ['과일', '과즙', '과일향']
            },
            'floral_notes': {
                'flower': ['꽃향', '플로럴', '장미', '라벤더', '쟈스민', '히비스커스'],
                'herbal_floral': ['허브', '민트', '로즈마리', '타임', '바질']
            },
            'grain_notes': {
                'rice': ['쌀', '백미', '찹쌀', '멥쌀', '쌀향', '곡물'],
                'wheat': ['밀', '소맥', '밀가루', '밀향'],
                'other_grain': ['보리', '옥수수', '수수', '조', '곡물']
            },
            'herbal_notes': {
                'herb': ['허브', '유기농 허브', '로즈마리', '타임', '바질', '민트'],
                'spice': ['생강', '계피', '후추', '강황', '카다멈'],
                'other_herbal': ['약초', '쑥', '인삼', '홍삼', '도라지']
            }
        }

    def extract_vector(self, text: str, abv: float = 0) -> Dict[str, float]:
        """
        텍스트에서 맛 벡터 추출 (세분화된 로직)

        Args:
            text: 분석할 텍스트
            abv: 알콜 도수

        Returns:
            맛 벡터 딕셔너리
        """
        if not text:
            text = ""

        vector = {
            'sweetness': 5.0,
            'body': 5.0,
            'carbonation': 5.0,
            'flavor': 5.0,
            'alcohol': self._abv_to_score(abv),
            'acidity': 5.0,
            'aroma_intensity': 5.0,
            'finish': 5.0
        }

        # 텍스트 분석 (세분화된 로직)
        for taste, keywords in self.taste_keywords.items():
            if taste == 'alcohol':
                continue

            score = 5.0  # 기본값

            # 각 레벨별 키워드 매칭
            very_high_count = sum(1 for kw in keywords['very_high'] if kw in text)
            high_count = sum(1 for kw in keywords['high'] if kw in text)
            medium_count = sum(1 for kw in keywords['medium'] if kw in text)
            low_count = sum(1 for kw in keywords['low'] if kw in text)
            very_low_count = sum(1 for kw in keywords['very_low'] if kw in text)

            # 점수 계산 (세분화)
            if very_high_count > 0:
                score = min(10.0, 8.0 + very_high_count * 0.5)
            elif high_count > 0:
                score = min(8.0, 6.0 + high_count * 0.4)
            elif medium_count > 0:
                score = 5.0 + medium_count * 0.1
            elif low_count > 0:
                score = max(3.0, 4.0 - low_count * 0.3)
            elif very_low_count > 0:
                score = max(1.0, 2.0 - very_low_count * 0.3)

            vector[taste] = round(score, 1)

        return vector

    def extract_notes(self, text: str) -> Dict[str, Dict[str, float]]:
        """
        텍스트에서 향 노트 추출

        Args:
            text: 분석할 텍스트

        Returns:
            향 노트 딕셔너리
        """
        if not text:
            text = ""

        notes = {
            'fruit_notes': {},
            'floral_notes': {},
            'grain_notes': {},
            'herbal_notes': {}
        }

        for note_type, categories in self.note_keywords.items():
            for category, keywords in categories.items():
                count = sum(1 for kw in keywords if kw in text)
                if count > 0:
                    # 0~10 사이 점수로 변환
                    score = min(10.0, count * 2.0)
                    notes[note_type][category] = round(score, 1)

        return notes

    def _abv_to_score(self, abv: float) -> float:
        """알콜 도수를 0~10 점으로 변환 (세분화)"""
        if abv <= 0:
            return 0.0
        elif abv <= 3:
            return 2.0
        elif abv <= 5:
            return 3.5
        elif abv <= 7:
            return 5.0
        elif abv <= 10:
            return 6.5
        elif abv <= 12:
            return 7.5
        elif abv <= 15:
            return 8.5
        elif abv <= 18:
            return 9.0
        else:
            return 10.0

    def _clean_awards(self, awards) -> Optional[str]:
        """awards NaN 처리"""
        if awards is None or (isinstance(awards, float) and str(awards) == 'nan'):
            return None
        return str(awards) if awards else None

    def process_makgeolli_data(self, input_file: str, output_file: str) -> List[Dict]:
        """
        막걸리 데이터에 고도화된 맛 벡터 추가

        Args:
            input_file: 입력 JSON 파일
            output_file: 출력 JSON 파일

        Returns:
            맛 벡터가 추가된 데이터 리스트
        """
        logger.info(f"고도화된 맛 벡터 추출 시작: {input_file}")

        # 데이터 로드
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 맛 벡터 추출
        for item in data:
            # 텍스트 결합
            text = f"{item.get('description', '')} {item.get('features', '')} {item.get('ingredients', '')}"

            # 맛 벡터 추출
            vector = self.extract_vector(text, item.get('abv', 0))
            item['taste_vector'] = vector

            # 향 노트 추출
            notes = self.extract_notes(text)
            item['taste_notes'] = notes

            # awards NaN 처리
            item['awards'] = self._clean_awards(item.get('awards'))

            logger.info(f"맛 벡터 추출: {item['name']}")

        # 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"저장 완료: {output_file}")
        logger.info(f"총 {len(data)}개 데이터 처리 완료")

        return data


def main():
    """메인 실행 함수"""
    extractor = EnhancedTasteVectorExtractor()

    # 막걸리 데이터 처리
    input_file = "data/processed/makgeolli_data.json"
    output_file = "data/processed/makgeolli_with_vectors_v2.json"

    if Path(input_file).exists():
        data = extractor.process_makgeolli_data(input_file, output_file)

        # 샘플 출력
        print("\n=== 샘플 데이터 ===")
        for item in data[:3]:
            print(f"\n이름: {item['name']}")
            print(f"맛 벡터: {item['taste_vector']}")
            print(f"향 노트: {item['taste_notes']}")
            print(f"수상 이력: {item['awards']}")
    else:
        logger.warning(f"입력 파일 없음: {input_file}")


if __name__ == "__main__":
    main()
