"""
신규 전통주 자동 맛 벡터 생성 파이프라인
CSV 파싱 → Gemini 라벨링 → 맛 벡터 생성
"""

import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import csv
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoPipeline:
    """신규 전통주 자동 맛 벡터 생성 파이프라인"""

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

        # 앙커 데이터 (실제 시음 기반 기준점)
        self.anchors = self._load_anchors()

        # 출력 디렉토리
        self.output_dir = Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_anchors(self) -> List[Dict]:
        """앙커 데이터 로드"""
        anchor_file = Path("data/anchors.json")

        if anchor_file.exists():
            with open(anchor_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('anchors', [])
        else:
            # 기본 앙커 데이터
            return [
                {
                    "name": "복순도가 복분자주",
                    "sweetness": 8.0,
                    "body": 5.0,
                    "carbonation": 2.0,
                    "flavor": 9.0,
                    "alcohol": 7.0,
                    "acidity": 7.0,
                    "aroma_intensity": 8.0,
                    "finish": 6.0,
                    "note": "실제 시음 기반 - 복분자의 달콤함과 풍미가 뚜렷함"
                },
                {
                    "name": "이동 생 쌀 막걸리",
                    "sweetness": 6.0,
                    "body": 6.0,
                    "carbonation": 4.0,
                    "flavor": 6.0,
                    "alcohol": 5.0,
                    "acidity": 5.0,
                    "aroma_intensity": 5.0,
                    "finish": 5.0,
                    "note": "실제 시음 기반 - 쌀 막걸리의 밸런스"
                },
                {
                    "name": "오산막걸리",
                    "sweetness": 5.0,
                    "body": 5.0,
                    "carbonation": 5.0,
                    "flavor": 5.0,
                    "alcohol": 5.0,
                    "acidity": 5.0,
                    "aroma_intensity": 5.0,
                    "finish": 5.0,
                    "note": "실제 시음 기반 - 표준 막걸리"
                },
                {
                    "name": "오미자 생막걸리",
                    "sweetness": 7.0,
                    "body": 4.0,
                    "carbonation": 6.0,
                    "flavor": 7.0,
                    "alcohol": 5.0,
                    "acidity": 8.0,
                    "aroma_intensity": 7.0,
                    "finish": 6.0,
                    "note": "실제 시음 기반 - 오미자의 산미와 풍미"
                },
                {
                    "name": "연천 율무 동동주",
                    "sweetness": 4.0,
                    "body": 7.0,
                    "carbonation": 3.0,
                    "flavor": 5.0,
                    "alcohol": 6.0,
                    "acidity": 4.0,
                    "aroma_intensity": 4.0,
                    "finish": 5.0,
                    "note": "실제 시음 기반 - 율무의 묵직한 바디감"
                }
            ]

    def parse_csv(self, csv_file: str) -> List[Dict]:
        """
        CSV 파일 파싱

        Args:
            csv_file: CSV 파일 경로

        Returns:
            파싱된 데이터 리스트
        """
        data = []

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # 빈 값 처리
                    cleaned_row = {k: (v if v else "") for k, v in row.items()}
                    data.append(cleaned_row)

            logger.info(f"CSV 파싱 완료: {len(data)}개 데이터")
            return data

        except Exception as e:
            logger.error(f"CSV 파싱 실패: {e}")
            return []

    def label_with_gemini(self, drink_data: Dict) -> Optional[Dict]:
        """
        Gemini를 활용한 맛 벡터 라벨링

        Args:
            drink_data: 전통주 데이터

        Returns:
            라벨링된 맛 벡터
        """
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY가 설정되지 않음")
            return None

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-pro')

            # 앙커 데이터를 프롬프트에 포함
            anchor_text = "\n".join([
                f"- {anchor['name']}: 단맛={anchor['sweetness']}, 바디감={anchor['body']}, "
                f"탄산={anchor['carbonation']}, 풍미={anchor['flavor']}, 도수={anchor['alcohol']}, "
                f"산미={anchor['acidity']}, 향기={anchor['aroma_intensity']}, 여운={anchor['finish']}"
                for anchor in self.anchors
            ])

            # 전통주 정보 구성
            drink_info = f"""
이름: {drink_data.get('name', '')}
설명: {drink_data.get('description', '')}
특징: {drink_data.get('features', '')}
원재료: {drink_data.get('ingredients', '')}
도수: {drink_data.get('abv', '')}%
양조장: {drink_data.get('brewery', '')}
지역: {drink_data.get('region', '')}
"""

            # 프롬프트 구성
            prompt = f"""
다음은 전통주에 대한 정보입니다:

{drink_info}

앙커 데이터 (실제 시음 기반 기준점):
{anchor_text}

이 전통주의 맛 벡터를 0~10 점으로 평가해주세요.
앙커 데이터를 참고하여 일관성 있게 평가해주세요.

평가 항목:
- sweetness (단맛): 0~10
- body (바디감): 0~10
- carbonation (탄산): 0~10
- flavor (풍미): 0~10
- alcohol (도수): 0~10
- acidity (산미): 0~10
- aroma_intensity (향기 강도): 0~10
- finish (여운): 0~10

답변 형식 (JSON):
{{
  "sweetness": 0.0,
  "body": 0.0,
  "carbonation": 0.0,
  "flavor": 0.0,
  "alcohol": 0.0,
  "acidity": 0.0,
  "aroma_intensity": 0.0,
  "finish": 0.0
}}
"""

            response = model.generate_content(prompt)
            result_text = response.text

            # JSON 파싱
            try:
                # JSON 부분 추출
                import re
                json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
                if json_match:
                    result_text = json_match.group(0)

                vector = json.loads(result_text)

                # 값 범위 확인
                for key in vector:
                    vector[key] = max(0.0, min(10.0, float(vector[key])))

                return vector

            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                logger.error(f"원본 응답: {result_text}")
                return None

        except Exception as e:
            logger.error(f"Gemini 라벨링 실패: {e}")
            return None

    def create_taste_vector(self, drink_data: Dict, use_gemini: bool = True) -> Dict:
        """
        맛 벡터 생성

        Args:
            drink_data: 전통주 데이터
            use_gemini: Gemini 사용 여부

        Returns:
            맛 벡터
        """
        # Gemini 라벨링
        if use_gemini:
            gemini_vector = self.label_with_gemini(drink_data)
            if gemini_vector:
                return gemini_vector

        # 기본 벡터 생성 (텍스트 기반)
        return self._create_basic_vector(drink_data)

    def _create_basic_vector(self, drink_data: Dict) -> Dict:
        """기본 맛 벡터 생성 (텍스트 기반)"""
        text = f"{drink_data.get('description', '')} {drink_data.get('features', '')} {drink_data.get('ingredients', '')}"

        # 기본 벡터
        vector = {
            'sweetness': 5.0,
            'body': 5.0,
            'carbonation': 5.0,
            'flavor': 5.0,
            'alcohol': self._abv_to_score(drink_data.get('abv', 0)),
            'acidity': 5.0,
            'aroma_intensity': 5.0,
            'finish': 5.0
        }

        # 텍스트 기반 조정
        if '달콤' in text or '단맛' in text or '과일' in text:
            vector['sweetness'] = min(10.0, vector['sweetness'] + 2.0)
        if '신맛' in text or '산미' in text or '새콤' in text:
            vector['acidity'] = min(10.0, vector['acidity'] + 2.0)
        if '묵직' in text or '바디' in text or '농밀' in text:
            vector['body'] = min(10.0, vector['body'] + 2.0)
        if '탄산' in text or '스파클링' in text or '거품' in text:
            vector['carbonation'] = min(10.0, vector['carbonation'] + 2.0)
        if '풍미' in text or '향기' in text or '맛' in text:
            vector['flavor'] = min(10.0, vector['flavor'] + 1.0)

        return vector

    def _abv_to_score(self, abv: float) -> float:
        """알콜 도수를 0~10 점으로 변환"""
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

    def process_csv(self, csv_file: str, output_file: str, use_gemini: bool = True) -> List[Dict]:
        """
        CSV 처리 파이프라인

        Args:
            csv_file: 입력 CSV 파일
            output_file: 출력 JSON 파일
            use_gemini: Gemini 사용 여부

        Returns:
            처리된 데이터 리스트
        """
        logger.info(f"파이프라인 시작: {csv_file}")

        # 1. CSV 파싱
        data = self.parse_csv(csv_file)
        if not data:
            logger.error("CSV 파싱 실패")
            return []

        # 2. 맛 벡터 생성
        processed_data = []
        for i, item in enumerate(data, 1):
            logger.info(f"처리 중 ({i}/{len(data)}): {item.get('name', 'Unknown')}")

            # 맛 벡터 생성
            taste_vector = self.create_taste_vector(item, use_gemini)

            # 데이터 구성
            processed_item = {
                'id': f"makgeolli_{i-1}",
                'name': item.get('name', ''),
                'abv': float(item.get('abv', 0)) if item.get('abv') else 0.0,
                'brewery': item.get('brewery', ''),
                'region': item.get('region', ''),
                'description': item.get('description', ''),
                'features': item.get('features', ''),
                'ingredients': item.get('ingredients', ''),
                'awards': item.get('awards', ''),
                'taste_vector': taste_vector,
                'created_at': datetime.now().isoformat()
            }

            processed_data.append(processed_item)

        # 3. 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)

        logger.info(f"저장 완료: {output_file}")
        logger.info(f"총 {len(processed_data)}개 데이터 처리 완료")

        return processed_data

    def add_new_drink(self, drink_data: Dict, output_file: str, use_gemini: bool = True) -> Dict:
        """
        신규 전통주 추가

        Args:
            drink_data: 전통주 데이터
            output_file: 출력 JSON 파일
            use_gemini: Gemini 사용 여부

        Returns:
            추가된 데이터
        """
        # 기존 데이터 로드
        existing_data = []
        if Path(output_file).exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

        # 맛 벡터 생성
        taste_vector = self.create_taste_vector(drink_data, use_gemini)

        # 새 데이터 구성
        new_id = f"makgeolli_{len(existing_data)}"
        new_item = {
            'id': new_id,
            'name': drink_data.get('name', ''),
            'abv': float(drink_data.get('abv', 0)) if drink_data.get('abv') else 0.0,
            'brewery': drink_data.get('brewery', ''),
            'region': drink_data.get('region', ''),
            'description': drink_data.get('description', ''),
            'features': drink_data.get('features', ''),
            'ingredients': drink_data.get('ingredients', ''),
            'awards': drink_data.get('awards', ''),
            'taste_vector': taste_vector,
            'created_at': datetime.now().isoformat()
        }

        # 데이터 추가
        existing_data.append(new_item)

        # 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        logger.info(f"신규 전통주 추가 완료: {new_item['name']}")

        return new_item


def main():
    """메인 실행 함수"""
    pipeline = AutoPipeline()

    print("=== 신규 전통주 자동 맛 벡터 생성 파이프라인 테스트 ===\n")

    # 1. 앙커 데이터 확인
    print("--- 1. 앙커 데이터 ---")
    for anchor in pipeline.anchors:
        print(f"{anchor['name']}: {anchor['note']}")

    # 2. 샘플 데이터 처리
    print("\n--- 2. 샘플 데이터 처리 ---")

    # 샘플 CSV 파일 생성
    sample_csv = "data/raw/sample_makgeolli.csv"
    sample_output = "data/processed/sample_makgeolli_with_vectors.json"

    Path("data/raw").mkdir(parents=True, exist_ok=True)

    sample_data = [
        {
            "name": "샘플 막걸리 1",
            "abv": "6.0",
            "brewery": "샘플 양조장",
            "region": "경기도",
            "description": "달콤하고 부드러운 막걸리",
            "features": "달콤한 맛, 부드러운 바디감",
            "ingredients": "쌀, 누룩, 물",
            "awards": ""
        },
        {
            "name": "샘플 막걸리 2",
            "abv": "5.0",
            "brewery": "샘플 양조장",
            "region": "강원도",
            "description": "새콤하고 청량한 막걸리",
            "features": "새콤한 산미, 청량한 탄산",
            "ingredients": "쌀, 오미자, 누룩, 물",
            "awards": ""
        }
    ]

    with open(sample_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sample_data[0].keys())
        writer.writeheader()
        writer.writerows(sample_data)

    # 파이프라인 실행
    processed_data = pipeline.process_csv(sample_csv, sample_output, use_gemini=False)

    # 결과 출력
    print("\n처리된 데이터:")
    for item in processed_data:
        print(f"\n이름: {item['name']}")
        print(f"맛 벡터: {item['taste_vector']}")

    # 3. 신규 전통주 추가 테스트
    print("\n--- 3. 신규 전통주 추가 ---")

    new_drink = {
        "name": "테스트 막걸리",
        "abv": "7.0",
        "brewery": "테스트 양조장",
        "region": "경상도",
        "description": "묵직하고 풍미가 풍부한 막걸리",
        "features": "묵직한 바디감, 풍부한 풍미",
        "ingredients": "찹쌀, 누룩, 물",
        "awards": ""
    }

    added_item = pipeline.add_new_drink(new_drink, sample_output, use_gemini=False)

    print(f"추가된 전통주: {added_item['name']}")
    print(f"맛 벡터: {added_item['taste_vector']}")


if __name__ == "__main__":
    main()
