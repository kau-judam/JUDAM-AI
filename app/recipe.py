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

            client = genai.Client(api_key=self.gemini_api_key)

            prompt = f"막걸리/탁주 양조 시 {main_ingredient}와 어울리는 서브재료를 {region} 지역 특산물 중심으로 5개 추천해줘. JSON 배열로만 답변."

            response = client.models.generate_content(model='models/gemini-1.5-flash', contents=prompt)
            result_text = response.text

            # JSON 파싱
            try:
                import re
                json_match = re.search(r'\[[\s\S]*\]', result_text)
                if json_match:
                    result_text = json_match.group(0)

                result = json.loads(result_text)

                if isinstance(result, list):
                    return {"sub_ingredients": result}
                else:
                    return {"sub_ingredients": []}

            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                logger.error(f"원본 응답: {result_text}")
                return {"sub_ingredients": []}

        except Exception as e:
            logger.error(f"서브재료 추천 실패: {e}")
            return {"sub_ingredients": []}

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

            response = client.models.generate_content(model='models/gemini-1.5-flash', contents=prompt)
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
            logger.error(f"맛 태그 추천 실패: {e}")
            return {"flavor_tags": []}

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

            response = client.models.generate_content(model='models/gemini-1.5-flash', contents=prompt)
            result_text = response.text.strip()

            return {"summary": result_text}

        except Exception as e:
            logger.error(f"요약문 생성 실패: {e}")
            return {"summary": ""}
