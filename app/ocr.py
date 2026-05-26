"""
양조장 인증 서류 OCR 분석
Gemini Vision 기반 3종 서류 판별 및 정보 추출
"""

import json
import os


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

            prompt = """이 이미지가 양조장 인증 서류인지 판단하고 정보를 추출해줘.

[인정되는 서류 3종]
1. 주류제조면허증 - 국세청 발급, 면허번호 포함
2. 사업자등록증 - 국세청 발급, 사업자등록번호 포함
3. 식품제조가공업 영업신고증 - 식약처 또는 지자체 발급

[추출 정보]
다음 JSON으로만 반환. 다른 말 없이.
{
  "document_type": "주류제조면허증/사업자등록증/식품제조가공업영업신고증/인식불가",
  "is_valid_document": true,
  "brewery_name": "업체명 또는 상호",
  "registration_number": "면허번호 또는 사업자번호 또는 신고번호",
  "owner_name": "대표자명",
  "address": "주소",
  "issue_date": "발급일 또는 등록일",
  "issuing_authority": "발급기관 (국세청/식약처/지자체)",
  "alcohol_types": [],
  "confidence": "high/medium/low",
  "rejection_reason": null
}"""

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
