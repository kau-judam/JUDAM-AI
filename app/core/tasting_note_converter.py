"""
테이스팅 노트 자동 변환 모듈
소믈리에 자유형 텍스트 또는 구조화된 점수를 맛 벡터 10축으로 변환
"""

import logging
import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TasteVector10(BaseModel):
    """10축 맛 벡터 모델"""
    sweetness: float = Field(..., ge=0, le=10, description="단맛 (0~10)")
    body: float = Field(..., ge=0, le=10, description="바디감 (0~10)")
    carbonation: float = Field(..., ge=0, le=10, description="탄산 (0~10)")
    flavor: float = Field(..., ge=0, le=10, description="풍미 (0~10)")
    alcohol: float = Field(..., ge=0, le=10, description="도수 (0~10)")
    acidity: float = Field(..., ge=0, le=10, description="산미 (0~10)")
    aroma_intensity: float = Field(..., ge=0, le=10, description="향기 강도 (0~10)")
    finish: float = Field(..., ge=0, le=10, description="여운 (0~10)")
    texture: float = Field(..., ge=0, le=10, description="질감 (0~10)")
    color: float = Field(..., ge=0, le=10, description="색상/탁도 (0~10)")


class TasteNotes(BaseModel):
    """맛 노트 모델"""
    fruit_notes: Dict[str, float] = Field(default_factory=dict, description="과일 향 노트")
    floral_notes: Dict[str, float] = Field(default_factory=dict, description="꽃 향 노트")
    grain_notes: Dict[str, float] = Field(default_factory=dict, description="곡물 향 노트")
    herbal_notes: Dict[str, float] = Field(default_factory=dict, description="허브 향 노트")


class StructuredTastingInput(BaseModel):
    """구조화된 테이스팅 점수 입력"""
    name: str = Field(..., description="술 이름")
    sweetness: int = Field(..., ge=1, le=10, description="단맛 (1~10)")
    body: int = Field(..., ge=1, le=10, description="바디감 (1~10)")
    carbonation: int = Field(..., ge=1, le=10, description="탄산 (1~10)")
    flavor: int = Field(..., ge=1, le=10, description="풍미 (1~10)")
    acidity: int = Field(..., ge=1, le=10, description="산미 (1~10)")
    탁도: str = Field(..., description="탁도 (맑고 투명, 살짝 뿌연, 뽀얗게 뿌연, 진하게 탁한)")
    향: List[str] = Field(default_factory=list, description="향 리스트")
    특이사항: Optional[str] = Field(None, description="특이사항")


class FreeTextTastingInput(BaseModel):
    """자유형 텍스트 테이스팅 입력"""
    name: str = Field(..., description="술 이름")
    tasting_note: str = Field(..., description="자유형 테이스팅 노트")


class TastingNoteOutput(BaseModel):
    """테이스팅 노트 변환 출력"""
    name: str
    taste_vector: TasteVector10
    taste_notes: TasteNotes
    source: str  # "structured" or "gemini_converted"


class TastingNoteConverter:
    """테이스팅 노트 변환기"""

    def __init__(self):
        # 탁도 매핑
        self.turbidity_map = {
            "맑고 투명": 1.0,
            "살짝 뿌연": 3.0,
            "뽀얗게 뿌연": 5.0,
            "진하게 탁한": 8.0
        }

        # 향 매핑
        self.aroma_map = {
            # 과일 향
            "복숭아": {"category": "fruit_notes", "key": "stone_fruit", "value": 8.0},
            "살구": {"category": "fruit_notes", "key": "stone_fruit", "value": 8.0},
            "딸기": {"category": "fruit_notes", "key": "berry", "value": 8.0},
            "산딸기": {"category": "fruit_notes", "key": "berry", "value": 8.0},
            "블루베리": {"category": "fruit_notes", "key": "berry", "value": 8.0},
            "유자": {"category": "fruit_notes", "key": "citrus", "value": 8.0},
            "레몬": {"category": "fruit_notes", "key": "citrus", "value": 8.0},
            "라임": {"category": "fruit_notes", "key": "citrus", "value": 8.0},
            "망고": {"category": "fruit_notes", "key": "tropical", "value": 8.0},
            "사과": {"category": "fruit_notes", "key": "apple", "value": 7.0},
            "배": {"category": "fruit_notes", "key": "apple", "value": 7.0},
            # 꽃 향
            "꽃향": {"category": "floral_notes", "key": "flower", "value": 7.0},
            "장미": {"category": "floral_notes", "key": "flower", "value": 7.0},
            "라벤더": {"category": "floral_notes", "key": "flower", "value": 7.0},
            # 허브 향
            "쑥": {"category": "herbal_notes", "key": "herb", "value": 7.0},
            "약초": {"category": "herbal_notes", "key": "herb", "value": 7.0},
            "생강": {"category": "herbal_notes", "key": "spice", "value": 7.0},
            "계피": {"category": "herbal_notes", "key": "spice", "value": 7.0},
            "허브": {"category": "herbal_notes", "key": "herb", "value": 7.0},
            # 곡물 향
            "쌀": {"category": "grain_notes", "key": "rice", "value": 7.0},
            "누룩향": {"category": "grain_notes", "key": "rice", "value": 7.0},
            "밀": {"category": "grain_notes", "key": "wheat", "value": 6.0},
            "보리": {"category": "grain_notes", "key": "wheat", "value": 6.0}
        }

        # Gemini API 초기화
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            logger.warning("GEMINI_API_KEY가 설정되지 않았습니다.")
            self.gemini_model = None

    def convert_structured(self, input_data: StructuredTastingInput) -> TastingNoteOutput:
        """
        구조화된 점수를 맛 벡터로 변환

        Args:
            input_data: 구조화된 테이스팅 점수

        Returns:
            테이스팅 노트 변환 출력
        """
        # 기본 맛 벡터 생성
        taste_vector = TasteVector10(
            sweetness=float(input_data.sweetness),
            body=float(input_data.body),
            carbonation=float(input_data.carbonation),
            flavor=float(input_data.flavor),
            alcohol=5.0,  # 기본값
            acidity=float(input_data.acidity),
            aroma_intensity=5.0,  # 기본값
            finish=5.0,  # 기본값
            texture=float(input_data.body),  # 바디감과 유사
            color=self.turbidity_map.get(input_data.탁도, 5.0)
        )

        # 향 노트 생성
        taste_notes = TasteNotes()
        for aroma in input_data.향:
            aroma_info = self.aroma_map.get(aroma)
            if aroma_info:
                category = getattr(taste_notes, aroma_info["category"])
                category[aroma_info["key"]] = aroma_info["value"]

        return TastingNoteOutput(
            name=input_data.name,
            taste_vector=taste_vector,
            taste_notes=taste_notes,
            source="structured"
        )

    def convert_free_text(self, input_data: FreeTextTastingInput) -> TastingNoteOutput:
        """
        자유형 텍스트를 맛 벡터로 변환

        Args:
            input_data: 자유형 텍스트 테이스팅 입력

        Returns:
            테이스팅 노트 변환 출력
        """
        if not self.gemini_model:
            raise ValueError("Gemini API가 초기화되지 않았습니다.")

        # Gemini 프롬프트
        prompt = f"""다음 전통주 테이스팅 노트를 읽고 각 항목을 0~10점으로 변환해줘.
술 이름: {input_data.name}
테이스팅 노트: {input_data.tasting_note}

sweetness(단맛): 0=드라이, 10=매우달콤
body(바디감): 0=가벼움, 10=묵직함
carbonation(탄산): 0=없음, 10=강함
flavor(풍미방향): 0=쌀/누룩전통향, 10=과일/꽃독특향
alcohol(도수감): 0=낮음(3도이하), 10=높음(15도이상)
acidity(산미): 0=없음, 10=강함
aroma_intensity(향강도): 0=없음, 10=매우강함
finish(끝맛여운): 0=깔끔, 10=길게남음
texture(질감): 0=매끄러움, 10=걸쭉함
color(탁도): 0=맑고투명, 10=진하게탁함

JSON으로만 답변해줘."""

        try:
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()

            # JSON 파싱
            import json
            # ```json ... ``` 형식 제거
            if response_text.startswith("```"):
                response_text = response_text.strip("`").replace("json", "").strip()

            parsed = json.loads(response_text)

            # 맛 벡터 생성
            taste_vector = TasteVector10(
                sweetness=parsed.get("sweetness", 5.0),
                body=parsed.get("body", 5.0),
                carbonation=parsed.get("carbonation", 5.0),
                flavor=parsed.get("flavor", 5.0),
                alcohol=parsed.get("alcohol", 5.0),
                acidity=parsed.get("acidity", 5.0),
                aroma_intensity=parsed.get("aroma_intensity", 5.0),
                finish=parsed.get("finish", 5.0),
                texture=parsed.get("texture", 5.0),
                color=parsed.get("color", 5.0)
            )

            # 향 노트 생성
            taste_notes = TasteNotes(
                fruit_notes=parsed.get("fruit_notes", {}),
                floral_notes=parsed.get("floral_notes", {}),
                grain_notes=parsed.get("grain_notes", {}),
                herbal_notes=parsed.get("herbal_notes", {})
            )

            return TastingNoteOutput(
                name=input_data.name,
                taste_vector=taste_vector,
                taste_notes=taste_notes,
                source="gemini_converted"
            )

        except Exception as e:
            logger.error(f"자유형 텍스트 변환 실패: {e}")
            raise


def main():
    """메인 실행 함수"""
    converter = TastingNoteConverter()

    print("=== 테이스팅 노트 변환 테스트 ===\n")

    # 테스트 케이스 1: 구조화된 점수
    print("--- 테스트 케이스 1: 구조화된 점수 ---")
    structured_input = StructuredTastingInput(
        name="꿀 막걸리",
        sweetness=7,
        body=8,
        carbonation=2,
        flavor=3,
        acidity=5,
        탁도="뽀얗게 뿌연",
        향=["복숭아", "쌀누룩향"],
        특이사항="여름에 차갑게 마시면 특히 맛있음"
    )
    result1 = converter.convert_structured(structured_input)
    print(f"이름: {result1.name}")
    print(f"소스: {result1.source}")
    print(f"맛 벡터: {result1.taste_vector.model_dump()}")
    print(f"맛 노트: {result1.taste_notes.model_dump()}\n")

    # 테스트 케이스 2: 자유형 텍스트
    print("--- 테스트 케이스 2: 자유형 텍스트 ---")
    free_text_input = FreeTextTastingInput(
        name="유자 막걸리",
        free_text="색은 맑고 투명하며, 첫 모금에 유자의 상큼한 향과 단맛이 올라옵니다. 입안에서 청량한 탄산감이 느껴지고, 끝맛은 깔끔하게 사라집니다."
    )
    try:
        result2 = converter.convert_free_text(free_text_input)
        print(f"이름: {result2.name}")
        print(f"소스: {result2.source}")
        print(f"맛 벡터: {result2.taste_vector.model_dump()}")
        print(f"맛 노트: {result2.taste_notes.model_dump()}")
    except Exception as e:
        print(f"자유형 텍스트 변환 실패: {e}")


if __name__ == "__main__":
    main()
