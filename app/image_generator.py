"""
전통주 이미지 생성기
1순위: Gemini 2.0 Flash Exp 네이티브 이미지 생성 (google-genai SDK)
2순위: Hugging Face Stable Diffusion (HUGGINGFACE_TOKEN 필요)
"""

import os
import base64
import io
import logging
import random
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 입력 구동 이미지 프롬프트 빌더
#   - 맛벡터(8축, 0~10) → 시각 언어, 재료/맛태그 → 소품, 지역 → 배경,
#     구도/조명/스타일은 입력 해시로 프리셋을 '회전'시켜 술마다 다르게.
#   - [피사체][색감][질감][소품][배경][조명][스타일] 섹션으로 조립.
# ─────────────────────────────────────────────────────────────────────────────

# 재료/맛태그 키워드(한글) → 시각 소품·가니시(영문)
_INGREDIENT_PROPS = {
    '딸기': 'fresh strawberries', '복숭아': 'sliced peaches', '사과': 'crisp apple slices',
    '배': 'asian pear wedges', '포도': 'grape clusters', '샤인머스캣': 'green muscat grapes',
    '감귤': 'tangerines', '유자': 'yuzu citrus', '자몽': 'grapefruit', '레몬': 'lemon',
    '블루베리': 'blueberries', '망고': 'mango cubes', '오미자': 'omija berries',
    '꿀': 'a honey dipper and honeycomb', '쌀': 'rice grains and rice ears',
    '찹쌀': 'glutinous rice', '고구마': 'roasted sweet potato', '밤': 'chestnuts',
    '잣': 'pine nuts', '인삼': 'ginseng root', '홍삼': 'red ginseng',
    '녹차': 'green tea leaves', '대나무': 'bamboo leaves', '쑥': 'mugwort sprigs',
    '생강': 'ginger root', '꽃': 'edible flower petals', '허브': 'fresh herb sprigs',
}

# 지역 키워드(한글) → 배경 분위기(영문)
_REGION_BACKGROUNDS = {
    '제주': 'volcanic basalt stone and a hazy ocean horizon',
    '강원': 'misty pine mountains and clean highland air',
    '철원': 'misty pine mountains and clean highland air',
    '전라': 'lush southern green tea fields at golden hour',
    '나주': 'lush southern orchards and warm sunlight',
    '보성': 'rolling green tea terraces',
    '담양': 'a serene bamboo grove',
    '경상': 'a weathered hanok courtyard with tiled roofs',
    '안동': 'a traditional hanok courtyard and old wooden beams',
    '충청': 'a rural fruit orchard in soft daylight',
    '경기': 'a tranquil countryside rice paddy',
    '인천': 'a coastal village backdrop',
}

# 입력 해시로 회전시킬 프리셋 (약한 무작위 변주)
_COMPOSITION = [
    'tight macro close-up with shallow depth of field',
    'a 45-degree hero angle on a low wooden table',
    'an overhead flat-lay arrangement',
    'a low dramatic angle looking up at the bottle',
]
_LIGHTING = [
    'warm golden-hour side light with long soft shadows',
    'soft diffused window light, airy and clean',
    'moody low-key chiaroscuro with a single warm key light',
    'bright high-key daylight, fresh and crisp',
]
_STYLE = [
    'premium editorial product photography, ultra-detailed',
    'rustic analog film look with gentle grain',
    'minimalist clean studio aesthetic, lots of negative space',
    'cinematic atmospheric mood, rich tones',
]


def _v(taste_vector: Optional[Dict[str, float]], axis: str, default: float = 5.0) -> float:
    if not taste_vector:
        return default
    try:
        return float(taste_vector.get(axis, default))
    except (TypeError, ValueError):
        return default


def _color_phrase(tv: Optional[Dict[str, float]]) -> str:
    """단맛↑ 골든톤, 산미↑ 밝고 신선한 하이라이트, 도수↑ 깊은 색."""
    sweet, acid, alcohol = _v(tv, 'sweetness'), _v(tv, 'acidity'), _v(tv, 'alcohol')
    if sweet >= 6.5:
        base = 'deep golden-amber, honeyed and glistening'
    elif sweet <= 3.5:
        base = 'pale, dry, restrained pale-straw tones'
    else:
        base = 'soft warm ivory tones'
    if acid >= 6.5:
        base += ', with bright fresh dewy highlights'
    if alcohol >= 7.0:
        base += ', a richer concentrated hue'
    return base


def _texture_phrase(tv: Optional[Dict[str, float]]) -> str:
    """탄산↑ 기포, 바디↑ 점성, 탁도(=바디 proxy)↑ 우윳빛·↓ 투명."""
    carb, body = _v(tv, 'carbonation'), _v(tv, 'body')
    parts = []
    if body >= 6.5:
        parts.append('thick viscous creamy body, cloudy milky and opaque (탁주 느낌)')
    elif body <= 3.5:
        parts.append('light thin body, clear and translucent')
    else:
        parts.append('a medium silky body')
    if carb >= 6.0:
        parts.append('lively rising bubbles and a sparkling effervescent surface, fine condensation on the glass')
    elif carb <= 3.5:
        parts.append('a still, smooth, flat surface')
    return ', '.join(parts)


def _vessel(tv: Optional[Dict[str, float]]) -> str:
    """바디 높으면 막걸리 사발, 낮으면 맑은 유리잔."""
    body = _v(tv, 'body')
    if body >= 6.5:
        return 'a rustic celadon makgeolli bowl'
    if body <= 3.5:
        return 'a slender clear glass'
    return 'a traditional ceramic cup'


def _props_phrase(name: str, flavor_tags: List[str]) -> str:
    hay = name + ' ' + ' '.join(flavor_tags or [])
    found = []
    for kw, prop in _INGREDIENT_PROPS.items():
        if kw in hay and prop not in found:
            found.append(prop)
    if not found:
        return 'a few simple seasonal garnishes'
    return ', '.join(found[:3])


def _background_phrase(region: Optional[str]) -> str:
    if region:
        for kw, bg in _REGION_BACKGROUNDS.items():
            if kw in region:
                return bg
    return 'a softly blurred hanok interior with hanji paper'


def _as_png_base64(image_base64: str) -> Optional[str]:
    """공급자 이미지 응답을 base64 PNG로 정규화한다."""
    try:
        from PIL import Image

        image_bytes = base64.b64decode(image_base64)
        with Image.open(io.BytesIO(image_bytes)) as image:
            output = io.BytesIO()
            image.convert("RGBA").save(output, format="PNG")
        return base64.b64encode(output.getvalue()).decode("ascii")
    except Exception as exc:
        logger.warning("이미지 PNG 변환 실패: %s", type(exc).__name__)
        return None


def build_image_prompt(name: str, description: str, flavor_tags: Optional[List[str]] = None,
                       region: Optional[str] = None, main_ingredient: Optional[str] = None,
                       sub_ingredients: Optional[List[str]] = None, concept: Optional[str] = None,
                       taste_vector: Optional[Dict[str, float]] = None,
                       seed: Optional[int] = None) -> str:
    """
    입력 구동 + 섹션 조립 이미지 프롬프트.
    seed 가 None 이면 이름+지역 해시로 고정 → 같은 술은 재현, 다른 술은 다른 프리셋.
    """
    flavor_tags = flavor_tags or []
    if seed is None:
        seed = abs(hash(f'{name}|{region}')) % (2 ** 32)
    rng = random.Random(seed)
    composition = rng.choice(_COMPOSITION)
    lighting = rng.choice(_LIGHTING)
    style = rng.choice(_STYLE)

    flavor_str = ', '.join(flavor_tags) if flavor_tags else 'traditional'
    ingredient_tags = [main_ingredient] + (sub_ingredients or []) if main_ingredient else (sub_ingredients or [])
    visual_tags = flavor_tags + [tag for tag in ingredient_tags if tag]
    sections = [
        f"[SUBJECT] A bottle and {_vessel(taste_vector)} of Korean traditional alcohol "
        f"'{name}' ({description or flavor_str}), concept: {concept or 'traditional'}, {composition}",
        f"[COLOR] {_color_phrase(taste_vector)}",
        f"[TEXTURE] {_texture_phrase(taste_vector)}",
        f"[PROPS] garnished with {_props_phrase(name, visual_tags)}; "
        f"ingredients: {', '.join(ingredient_tags) or 'unspecified'}; flavor notes: {flavor_str}",
        f"[BACKGROUND] region: {region or 'unspecified'}, {_background_phrase(region)}",
        f"[LIGHTING] {lighting}",
        f"[STYLE] {style}, photorealistic, high resolution, no text, no watermark",
    ]
    return '\n'.join(sections)


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
                       region: Optional[str] = None,
                       main_ingredient: Optional[str] = None,
                       sub_ingredients: Optional[List[str]] = None,
                       concept: Optional[str] = None,
                       taste_vector: Optional[Dict[str, float]] = None,
                       seed: Optional[int] = None) -> dict:
        if not self.enabled:
            return {"status": "disabled", "message": "GEMINI_API_KEY가 설정되지 않았습니다."}

        try:
            # 1단계: 입력 구동 구조화 프롬프트 (맛벡터·재료·지역 반영, 프리셋 회전)
            image_prompt = build_image_prompt(
                name, description, flavor_tags or [], region, main_ingredient,
                sub_ingredients or [], concept, taste_vector, seed
            )
            logger.info(f"이미지 프롬프트 생성 완료: {image_prompt[:80]}")

            # 2단계: Gemini 네이티브 이미지 생성 시도
            try:
                image_b64, mime_type = await self._generate_with_gemini(image_prompt)
                png_b64 = _as_png_base64(image_b64) if image_b64 else None
                if png_b64:
                    logger.info(f"Gemini 이미지 생성 성공 ({mime_type})")
                    return {
                        "status": "success",
                        "image_base64": png_b64,
                        "mime_type": "image/png",
                        "model_used": self.gemini_image_model,
                        "prompt_used": image_prompt,
                        "message": f"Gemini {self.gemini_image_model}로 이미지 생성 완료"
                    }
            except Exception as gemini_err:
                logger.warning(f"Gemini 이미지 생성 실패, HF로 fallback: {gemini_err}")

            # 3단계: HF Stable Diffusion fallback
            image_b64 = await self._generate_with_hf(image_prompt)
            png_b64 = _as_png_base64(image_b64) if image_b64 else None
            if png_b64:
                return {
                    "status": "success",
                    "image_base64": png_b64,
                    "mime_type": "image/png",
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
