"""
전통주 이미지 생성기
Gemini로 프롬프트 생성 → Hugging Face Stable Diffusion으로 이미지 생성
"""

import os
import httpx
import base64
import google.generativeai as genai
from typing import Optional, List


class ImageGenerator:
    def __init__(self):
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        self.hf_token = os.getenv('HUGGINGFACE_TOKEN', '')
        self.hf_model = "stabilityai/stable-diffusion-xl-base-1.0"
        self.enabled = bool(self.gemini_key)

    async def generate_prompt(self, name: str, description: str,
                               flavor_tags: List[str], region: Optional[str] = None) -> str:
        genai.configure(api_key=self.gemini_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')

        flavor_str = ', '.join(flavor_tags) if flavor_tags else '전통적인'
        region_str = f'{region} 지역의 ' if region else ''

        prompt_request = f"""
다음 전통주 상품 사진에 어울리는 이미지 생성 프롬프트를 영어로 만들어줘.
전통주명: {name}
설명: {description}
맛 특징: {flavor_str}
지역: {region_str}

요구사항:
- 전통 도자기 잔 또는 전통주 병
- 한국 전통 소품 배경 (한지, 대나무, 도자기)
- 고급스러운 상품 사진 스타일
- 자연광, 따뜻한 톤
- 50단어 이내 영어 프롬프트만 반환. 다른 말 없이.
"""
        response = await model.generate_content_async(prompt_request)
        return response.text.strip()

    async def generate_image_hf(self, prompt: str) -> Optional[str]:
        if not self.hf_token:
            return None
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
            return {"status": "disabled",
                    "message": "이미지 생성 기능이 비활성화되어 있습니다."}
        try:
            image_prompt = await self.generate_prompt(
                name, description, flavor_tags or [], region
            )
            image_b64 = await self.generate_image_hf(image_prompt)
            if image_b64:
                return {
                    "status": "success",
                    "image_base64": image_b64,
                    "prompt_used": image_prompt,
                    "format": "jpeg"
                }
            else:
                return {
                    "status": "prompt_only",
                    "prompt_used": image_prompt,
                    "message": "HUGGINGFACE_TOKEN 설정 시 이미지 자동 생성 가능합니다."
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}
