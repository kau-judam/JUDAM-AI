"""
전통주 이미지 생성기
1순위: Gemini 2.0 Flash Exp 네이티브 이미지 생성 (google-genai SDK)
2순위: Hugging Face Stable Diffusion (HUGGINGFACE_TOKEN 필요)
"""

import os
import base64
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class ImageGenerator:
    def __init__(self):
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        self.hf_token = os.getenv('HUGGINGFACE_TOKEN', '')
        self.hf_model = "stabilityai/stable-diffusion-xl-base-1.0"
        self.enabled = bool(self.gemini_key)
        self.gemini_image_model = "gemini-2.5-flash-image"

    async def _build_image_prompt(self, name: str, description: str,
                                   flavor_tags: List[str], region: Optional[str]) -> str:
        """Gemini로 영문 이미지 프롬프트 생성"""
        from google import genai as google_genai

        client = google_genai.Client(api_key=self.gemini_key)
        flavor_str = ', '.join(flavor_tags) if flavor_tags else 'traditional'
        region_str = f'{region}, ' if region else ''

        req = (
            f"Write a 50-word English image generation prompt for a Korean traditional alcohol product photo.\n"
            f"Product: {name}\n"
            f"Description: {description}\n"
            f"Flavor: {flavor_str}\n"
            f"Region: {region_str}Korea\n"
            f"Style: traditional ceramic cup, Korean props (hanji, bamboo, celadon), "
            f"warm natural light, premium product photography. Return only the prompt."
        )
        resp = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=req
        )
        return resp.text.strip()

    async def _generate_with_gemini(self, prompt: str) -> tuple:
        """Gemini 2.0 Flash Exp 네이티브 이미지 생성. (image_b64, mime_type) 반환"""
        from google import genai as google_genai
        from google.genai import types

        client = google_genai.Client(api_key=self.gemini_key)
        image_prompt = f"Generate a high-quality product photo: {prompt}"

        resp = await client.aio.models.generate_content(
            model=self.gemini_image_model,
            contents=image_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            )
        )

        for part in resp.candidates[0].content.parts:
            if part.inline_data is not None:
                b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                return b64, part.inline_data.mime_type

        return None, None

    async def _generate_with_hf(self, prompt: str) -> Optional[str]:
        """Hugging Face Stable Diffusion 이미지 생성"""
        if not self.hf_token:
            return None
        import httpx
        url = f"https://api-inference.huggingface.co/models/{self.hf_model}"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(url, headers=headers, json={"inputs": prompt})
            if r.status_code == 200:
                return base64.b64encode(r.content).decode('utf-8')
        return None

    async def generate(self, name: str, description: str,
                       flavor_tags: Optional[List[str]] = None,
                       region: Optional[str] = None) -> dict:
        if not self.enabled:
            return {"status": "disabled", "message": "GEMINI_API_KEY가 설정되지 않았습니다."}

        try:
            # 1단계: 이미지 프롬프트 생성
            image_prompt = await self._build_image_prompt(
                name, description, flavor_tags or [], region
            )
            logger.info(f"이미지 프롬프트 생성 완료: {image_prompt[:80]}")

            # 2단계: Gemini 네이티브 이미지 생성 시도
            try:
                image_b64, mime_type = await self._generate_with_gemini(image_prompt)
                if image_b64:
                    logger.info(f"Gemini 이미지 생성 성공 ({mime_type})")
                    return {
                        "status": "success",
                        "image_base64": image_b64,
                        "mime_type": mime_type,
                        "model_used": self.gemini_image_model,
                        "prompt_used": image_prompt,
                        "message": f"Gemini {self.gemini_image_model}로 이미지 생성 완료"
                    }
            except Exception as gemini_err:
                logger.warning(f"Gemini 이미지 생성 실패, HF로 fallback: {gemini_err}")

            # 3단계: HF Stable Diffusion fallback
            image_b64 = await self._generate_with_hf(image_prompt)
            if image_b64:
                return {
                    "status": "success",
                    "image_base64": image_b64,
                    "mime_type": "image/jpeg",
                    "model_used": self.hf_model,
                    "prompt_used": image_prompt,
                    "message": "Stable Diffusion으로 이미지 생성 완료"
                }

            # 프롬프트만 반환
            return {
                "status": "prompt_only",
                "prompt_used": image_prompt,
                "model_used": "none",
                "message": "이미지 생성 실패. HUGGINGFACE_TOKEN 또는 Gemini 이미지 모델 권한을 확인하세요."
            }

        except Exception as e:
            logger.error(f"이미지 생성 오류: {e}")
            return {"status": "error", "message": str(e)}
