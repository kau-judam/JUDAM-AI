"""
양조장 인증 서류 OCR 분석
Gemini Vision 기반 서류 판별 및 정보 추출.

지원 서류는 SUPPORTED_DOC_TYPES 레지스트리로 관리한다.
→ 새 서류를 추가하려면 이 리스트에 dict 한 줄만 append 하면 된다 (프롬프트 자동 반영).
"""

import json
import os

# 지원 서류 레지스트리. (type=판별 라벨, hint=식별 단서, id_field=핵심 식별번호)
SUPPORTED_DOC_TYPES = [
    {"type": "사업자등록증", "hint": "국세청/세무서 발급, 사업자등록번호(000-00-00000)", "id_field": "사업자등록번호"},
    {"type": "신분증", "hint": "주민등록증/운전면허증, 성명·주민등록번호 또는 면허번호", "id_field": "주민등록번호 또는 운전면허번호"},
    {"type": "통신판매업신고증", "hint": "시장·군수·구청장 발급, 신고번호(제 YYYY-지역-NNNNN 호)", "id_field": "통신판매업 신고번호"},
    {"type": "주류통신판매승인서", "hint": "관할 세무서장 발급, 전통주 통신판매 승인번호", "id_field": "승인번호"},
    {"type": "전통주제조면허증", "hint": "관할 세무서장 발급, 면허번호·면허종류(전통주/탁주/약주/청주)", "id_field": "면허번호"},
    {"type": "주류제조면허증", "hint": "국세청/세무서 발급, 주류 제조면허번호", "id_field": "면허번호"},
    {"type": "식품제조가공업영업신고증", "hint": "식약처 또는 지자체 발급, 영업신고번호", "id_field": "영업신고번호"},
]


def _build_ocr_prompt() -> str:
    """레지스트리로부터 OCR 프롬프트 생성."""
    lines = []
    for i, d in enumerate(SUPPORTED_DOC_TYPES, 1):
        lines.append(f"{i}. {d['type']} - {d['hint']}")
    doc_list = "\n".join(lines)
    type_enum = "/".join(d["type"] for d in SUPPORTED_DOC_TYPES) + "/인식불가"
    return f"""이 파일이 양조장 인증/신원 서류인지 판단하고 정보를 추출해줘.

[인정되는 서류 종류]
{doc_list}

[판별 기준]
- 위 종류 중 하나에 해당하고 핵심 식별번호가 읽히면 is_valid_document=true.
- 어느 종류에도 맞지 않거나 식별번호를 읽을 수 없으면 document_type="인식불가", is_valid_document=false, rejection_reason 명시.

[추출 정보]
다음 JSON으로만 반환. 다른 말 없이.
{{
  "document_type": "{type_enum}",
  "is_valid_document": true,
  "brewery_name": "업체명/상호/제조장명 (신분증이면 빈 문자열)",
  "registration_number": "해당 서류의 핵심 식별번호 (사업자번호/면허번호/신고번호/승인번호/주민등록번호)",
  "business_number": "문서에 사업자등록번호가 있으면 000-00-00000 형식, 없으면 빈 문자열",
  "owner_name": "대표자명 또는 신분증 성명",
  "address": "주소 또는 소재지",
  "issue_date": "발급일/등록일/면허일/승인일",
  "issuing_authority": "발급기관 (세무서장/국세청/구청장/시장 등)",
  "alcohol_types": [],
  "confidence": "high/medium/low",
  "rejection_reason": null,
  "raw_text": "문서에서 읽은 전체 텍스트. 줄바꿈을 유지하고 추측해서 채우지 말 것"
}}"""


class BreweryOCR:
    def __init__(self):
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        self.enabled = bool(self.gemini_key)

    async def extract_brewery_info(self, image_base64: str, mime_type: str = 'image/jpeg') -> dict:
        if not self.enabled:
            return {"status": "disabled", "message": "OCR 기능이 비활성화되어 있습니다."}

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.gemini_key)

            prompt = _build_ocr_prompt()

            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=_decode_base64(image_base64), mime_type=mime_type),
                ]
            )
            text = response.text.strip().replace('```json', '').replace('```', '').strip()
            result = json.loads(text)

            return {
                "status": "success",
                "extracted": result,
                "is_valid": result.get('is_valid_document', False),
                "confidence": result.get('confidence', 'low'),
                "document_type": result.get('document_type', '인식불가')
            }

        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"JSON 파싱 실패: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


def _decode_base64(b64_string: str) -> bytes:
    import base64
    # padding 보정
    padding = 4 - len(b64_string) % 4
    if padding != 4:
        b64_string += '=' * padding
    return base64.b64decode(b64_string)
