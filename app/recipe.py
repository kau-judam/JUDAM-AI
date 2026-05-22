"""
레시피 AI 클라이언트
Gemini API를 활용한 레시피 추천 기능
"""

import logging
import os
import json
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini 에러 관련 상수
_QUOTA_MSG = "현재 AI 서비스가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요."
_CONN_MSG  = "AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."


def _is_quota_error(e: Exception) -> bool:
    """429 / quota exceeded 에러 감지"""
    s = str(e)
    return '429' in s or 'quota exceeded' in s.lower() or 'resource_exhausted' in s.lower()


def _gemini_error_message(e: Exception) -> str:
    """에러 종류에 맞는 한글 메시지 반환"""
    if _is_quota_error(e):
        return _QUOTA_MSG
    return _CONN_MSG


class RecipeAI:
    """레시피 AI 클라이언트"""

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    async def suggest_sub_ingredients(self, main_ingredient: str, region: str) -> Dict[str, List[str]]:
        """
        서브재료 추천

        Args:
            main_ingredient: 메인 재료
            region: 지역

        Returns:
            서브재료 리스트
        """
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY가 설정되지 않음")
            return {"sub_ingredients": []}

        try:
            import google.genai as genai
            import re

            client = genai.Client(api_key=self.gemini_api_key)

            prompt = (
                f"전통주 지리적 표시제 기준으로 {region} 내 시/군 단위 특산물 기반 "
                f"서브재료 5개 추천해줘. 인접 지역 특산물은 제외하고 해당 지역 내 "
                f"특산물만 추천. 각 재료 옆에 원산지 시/군명 포함.\n"
                f"입력: 메인재료={main_ingredient}, 지역={region}\n"
                f'출력: {{"sub_ingredients": ["이천 쌀", "여주 고구마", ...]}}\n'
                f"다른 말 없이 JSON만 반환."
            )

            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt,
                config={"max_output_tokens": 200}
            )
            result_text = response.text.strip()
            logger.info(f"Gemini 서브재료 응답: {result_text}")

            try:
                # 객체 형태 {"sub_ingredients": [...]} 우선 파싱
                obj_match = re.search(r'\{[\s\S]*\}', result_text)
                if obj_match:
                    parsed = json.loads(obj_match.group(0))
                    if "sub_ingredients" in parsed and isinstance(parsed["sub_ingredients"], list):
                        return {"sub_ingredients": parsed["sub_ingredients"]}

                # fallback: 배열 형태 [...]
                arr_match = re.search(r'\[[\s\S]*\]', result_text)
                if arr_match:
                    parsed = json.loads(arr_match.group(0))
                    if isinstance(parsed, list):
                        if parsed and isinstance(parsed[0], dict):
                            return {"sub_ingredients": [
                                item.get("name") or item.get("ingredient") or item.get("재료명") or item.get("재료", "")
                                for item in parsed
                                if item.get("name") or item.get("ingredient") or item.get("재료명") or item.get("재료")
                            ]}
                        return {"sub_ingredients": parsed}

                return {"sub_ingredients": []}

            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}, 원본: {result_text}")
                return {"sub_ingredients": []}

        except Exception as e:
            msg = _gemini_error_message(e)
            logger.error(f"서브재료 추천 실패: {e}")
            raise RuntimeError(msg) from e

    async def suggest_flavor_tags(
        self,
        title: str,
        main_ingredient: str,
        sub_ingredients: List[str],
        abv_range: str
    ) -> Dict[str, List[str]]:
        """
        맛 태그 추천

        Args:
            title: 제목
            main_ingredient: 메인 재료
            sub_ingredients: 서브 재료 리스트
            abv_range: 도수 범위

        Returns:
            맛 태그 리스트
        """
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY가 설정되지 않음")
            return {"flavor_tags": []}

        try:
            import google.genai as genai

            client = genai.Client(api_key=self.gemini_api_key)

            sub_ingredients_str = ", ".join(sub_ingredients) if sub_ingredients else "없음"

            prompt = f"다음 막걸리 레시피를 보고 지향하는 맛 태그를 5개 이내로 생성해줘. JSON 배열로만 답변. 제목:{title} 메인재료:{main_ingredient} 서브재료:{sub_ingredients_str} 도수:{abv_range}"

            response = await client.aio.models.generate_content(model='gemini-2.5-flash-lite', contents=prompt)
            result_text = response.text

            # JSON 파싱
            try:
                import re
                json_match = re.search(r'\[[\s\S]*\]', result_text)
                if json_match:
                    result_text = json_match.group(0)

                result = json.loads(result_text)

                if isinstance(result, list):
                    return {"flavor_tags": result}
                else:
                    return {"flavor_tags": []}

            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                logger.error(f"원본 응답: {result_text}")
                return {"flavor_tags": []}

        except Exception as e:
            msg = _gemini_error_message(e)
            logger.error(f"맛 태그 추천 실패: {e}")
            raise RuntimeError(msg) from e

    async def validate_recipe(
        self,
        title: str,
        main_ingredient: str,
        sub_ingredients: List[str],
        abv_range: str,
        flavor_tags: List[str],
        description: str = None
    ) -> Dict:
        """
        레시피 제작 가능성 검토

        Args:
            title: 레시피 제목
            main_ingredient: 메인 재료
            sub_ingredients: 서브 재료 리스트
            abv_range: 목표 도수 범위
            flavor_tags: 맛 태그
            description: 추가 설명

        Returns:
            feasibility, score, issues, suggestions, summary
        """
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY가 설정되지 않음")
            return {
                "feasibility": "unknown",
                "score": 0,
                "issues": ["Gemini API 키가 설정되지 않았습니다."],
                "suggestions": [],
                "summary": "검토 불가"
            }

        try:
            import google.genai as genai
            import re

            client = genai.Client(api_key=self.gemini_api_key)

            sub_str = ", ".join(sub_ingredients) if sub_ingredients else "없음"
            tags_str = ", ".join(flavor_tags) if flavor_tags else "없음"
            desc_str = description or "없음"

            prompt = (
                "전통주 양조 전문가로서 아래 레시피의 제작 가능성을 검토해줘.\n"
                "재료 조합의 적절성, 도수 실현 가능성, 맛 밸런스를 분석하고\n"
                "JSON으로만 반환해줘.\n"
                "{\n"
                '  "feasibility": "high/medium/low",\n'
                '  "score": 0~100,\n'
                '  "issues": ["문제점1", "문제점2"],\n'
                '  "suggestions": ["개선안1", "개선안2"],\n'
                '  "summary": "한 줄 검토 결과"\n'
                "}\n\n"
                f"제목: {title}\n"
                f"메인재료: {main_ingredient}\n"
                f"서브재료: {sub_str}\n"
                f"목표도수: {abv_range}\n"
                f"맛태그: {tags_str}\n"
                f"설명: {desc_str}"
            )

            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt,
                config={"max_output_tokens": 300}
            )
            result_text = response.text.strip()
            logger.info(f"Gemini 레시피 검토 응답: {result_text[:200]}")

            obj_match = re.search(r'\{[\s\S]*\}', result_text)
            if obj_match:
                parsed = json.loads(obj_match.group(0))
                return {
                    "feasibility": parsed.get("feasibility", "unknown"),
                    "score": int(parsed.get("score", 0)),
                    "issues": parsed.get("issues", []),
                    "suggestions": parsed.get("suggestions", []),
                    "summary": parsed.get("summary", "")
                }

            return {
                "feasibility": "unknown",
                "score": 0,
                "issues": ["응답 파싱 실패"],
                "suggestions": [],
                "summary": result_text[:100]
            }

        except Exception as e:
            msg = _gemini_error_message(e)
            logger.error(f"레시피 검토 실패: {e}")
            raise RuntimeError(msg) from e

    async def suggest_summary(
        self,
        title: str,
        main_ingredient: str,
        sub_ingredients: List[str],
        abv_range: str,
        flavor_tags: List[str],
        concept: str = None
    ) -> Dict[str, str]:
        """
        요약문 생성

        Args:
            title: 제목
            main_ingredient: 메인 재료
            sub_ingredients: 서브 재료 리스트
            abv_range: 도수 범위
            flavor_tags: 맛 태그 리스트
            concept: 컨셉

        Returns:
            요약문
        """
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY가 설정되지 않음")
            return {"summary": ""}

        try:
            import google.genai as genai

            client = genai.Client(api_key=self.gemini_api_key)

            sub_ingredients_str = ", ".join(sub_ingredients) if sub_ingredients else "없음"
            flavor_tags_str = ", ".join(flavor_tags) if flavor_tags else "없음"
            concept_str = concept if concept else "없음"

            prompt = f"다음 전통주 레시피/펀딩 프로젝트의 요약문을 3문장으로 작성해줘. 텍스트로만 답변. 제목:{title} 메인재료:{main_ingredient} 서브재료:{sub_ingredients_str} 도수:{abv_range} 맛태그:{flavor_tags_str} 컨셉:{concept_str}"

            response = await client.aio.models.generate_content(model='gemini-2.5-flash-lite', contents=prompt)
            result_text = response.text.strip()

            return {"summary": result_text}

        except Exception as e:
            msg = _gemini_error_message(e)
            logger.error(f"요약문 생성 실패: {e}")
            raise RuntimeError(msg) from e
