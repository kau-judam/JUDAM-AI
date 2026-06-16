"""
레시피 AI 클라이언트
Gemini API를 활용한 레시피 추천 기능
"""

import logging
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 농사로 지역특산물 수집 결과 (scripts/collect_local_products.py 산출물)
_NONGSARO_REGION_MAP_PATH = Path("data/ingredient_region_map.json")
_NONGSARO_REGION_MAP: Optional[Dict[str, List[str]]] = None
_LOCAL_PRODUCTS_PATH = Path("data/local_products.json")
_LOCAL_PRODUCTS: Optional[List[Dict]] = None


def _has_rice_text(value: object) -> bool:
    """품목명에 '쌀' 글자가 들어 있으면 True. 서브재료·지역조회 전 경로 차단 기준."""
    return "쌀" in str(value or "")


def _filter_rice_sub_ingredients(sub_ingredients: List[str]) -> List[str]:
    """서브재료 목록에서 '쌀' 포함 품목을 제거한다."""
    return [item for item in sub_ingredients if not _has_rice_text(item)]


def _load_nongsaro_region_map() -> Dict[str, List[str]]:
    """특산물명 → 지역목록 매핑 로드. ' > ' 구분자는 공백으로 정규화. 없으면 빈 dict."""
    global _NONGSARO_REGION_MAP
    if _NONGSARO_REGION_MAP is None:
        try:
            with open(_NONGSARO_REGION_MAP_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            _NONGSARO_REGION_MAP = {
                name: [r.replace(" > ", " ").strip() for r in regions]
                for name, regions in raw.items()
            }
            logger.info(f"농사로 지역특산물 매핑 로드: {len(_NONGSARO_REGION_MAP)}개")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"농사로 매핑 로드 실패({e}) → 하드코딩 fallback 사용")
            _NONGSARO_REGION_MAP = {}
    return _NONGSARO_REGION_MAP


def _match_nongsaro_regions(ingredient: str) -> List[str]:
    """농사로 매핑에서 ingredient 에 해당하는 지역목록 반환 (없으면 [])."""
    if not ingredient or not ingredient.strip():
        return []  # 빈 입력은 substring 매칭으로 전 항목과 오매칭되므로 차단
    if _has_rice_text(ingredient):
        return []
    nmap = _load_nongsaro_region_map()
    if not nmap:
        return []
    if ingredient in nmap:
        return list(nmap[ingredient])
    matched: List[str] = []
    for name, regions in nmap.items():
        if ingredient in name or name in ingredient:
            for r in regions:
                if r not in matched:
                    matched.append(r)
    return matched[:10]


def _load_local_products() -> List[Dict]:
    """농사로 수집 특산물 원본을 로드한다."""
    global _LOCAL_PRODUCTS
    if _LOCAL_PRODUCTS is None:
        try:
            with open(_LOCAL_PRODUCTS_PATH, encoding="utf-8") as file:
                loaded = json.load(file)
            _LOCAL_PRODUCTS = loaded if isinstance(loaded, list) else []
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.warning("농사로 특산물 원본 로드 실패: %s", type(exc).__name__)
            _LOCAL_PRODUCTS = []
    return _LOCAL_PRODUCTS


def _region_matches(area: str, region: str) -> bool:
    """수집 데이터의 광역·기초 지역 표기와 요청 지역을 비교한다."""
    normalized_area = " ".join(str(area or "").replace(">", " ").split())
    normalized_region = " ".join(str(region or "").replace(">", " ").split())
    return bool(normalized_region and normalized_region in normalized_area)


# ── 서브재료 화이트리스트 (막걸리 부재료로 적합한 핵심 품목만 통과) ──
# 제외는 substring 오매칭이 우려되는 키워드(차·김·주·청·죽·묘·식초 등)는 'endswith(접미)'로,
# 채소·베이스·시설·비식품은 'substring'으로 비대칭 적용한다. 화이트는 '토큰 포함'으로 정규화.
_SUB_BASE_EXCLUDE = ("쌀", "찹쌀", "현미", "보리")                       # 곡물 베이스(쌀류)
_SUB_VEG_EXCLUDE = ("배추", "양배추", "감자", "고구마줄기",
                    "양파", "마늘", "버섯", "죽순", "풋고추", "들깨", "작두콩")  # 채소·나물
_SUB_NONFOOD_EXCLUDE = ("담배", "염색")                                 # 비식품
_SUB_FACILITY_EXCLUDE = ("판매처", "조합", "법인", "농원", "농장", "단지", "배양근")  # 시설·상품명
_SUB_PROC_SUFFIX = ("즙", "주", "청", "식초", "와인", "빵", "떡", "한과", "유과",
                    "엿", "죽", "오일", "달걀", "죽염", "잼", "된장", "고추장",
                    "막걸리", "가공식품", "식품", "쫀득이", "빼떼기", "감미료")  # 가공 접미
# (token, canonical) — 앞쪽(더 구체적)부터 검사해 정규화. '배추'·'감자'는 위에서 먼저 제외됨.
_SUB_WHITELIST = (
    ("샤인머스캣", "포도"), ("거봉", "포도"),
    ("산딸기", "산딸기"),
    ("곶감", "감"), ("단감", "감"), ("대봉", "감"),
    ("무화과", "무화과"), ("복숭아", "복숭아"),
    ("사과", "사과"), ("포도", "포도"), ("딸기", "딸기"), ("매실", "매실"),
    ("유자", "유자"), ("오미자", "오미자"), ("인삼", "인삼"), ("잣", "잣"),
    ("녹차", "녹차"), ("고구마", "고구마"),
    ("배", "배"), ("감", "감"),
)


def _filter_regions_with_sub(regions: List[str], main_ingredient: str) -> List[str]:
    """지역 목록 중 '화이트리스트 통과 서브재료가 1개 이상' 있는 지역만 남긴다.
    각 특산물 name 을 1회만 normalize 한 뒤 지역 substring 매칭으로 판정(성능)."""
    if _has_rice_text(main_ingredient):
        return []
    prods = []
    for p in _load_local_products():
        canon = _normalize_sub_ingredient(p.get("name"))
        if canon and canon != main_ingredient:
            area = " ".join(str(p.get("area") or "").replace(">", " ").split())
            prods.append((canon, area))
    kept = []
    for r in regions:
        nr = " ".join(str(r or "").replace(">", " ").split())
        if nr and any(nr in area for _, area in prods):
            kept.append(r)
    return kept


def _normalize_sub_ingredient(name: str):
    """후보 name → 막걸리 부재료 핵심 품목으로 정규화. 부적합/비화이트면 None."""
    n = str(name or "").strip()
    if not n:
        return None
    if _has_rice_text(n):
        return None
    # 1) 복합·다품목 문자열 차단
    if any(c in n for c in (",", "/", "·", "&")) or "  " in n:
        return None
    # 2) 명시 제외 (화이트 매칭보다 먼저 — substring 우선순위)
    if any(k in n for k in _SUB_BASE_EXCLUDE):
        return None
    if any(k in n for k in _SUB_VEG_EXCLUDE):
        return None
    if any(k in n for k in _SUB_NONFOOD_EXCLUDE):
        return None
    if any(k in n for k in _SUB_FACILITY_EXCLUDE):
        return None
    if n.endswith("묘") or n.endswith("김"):
        return None
    if n.endswith("차") and not n.endswith("녹차"):   # 유자차·감잎차 제외, 녹차는 통과
        return None
    if any(n.endswith(suf) for suf in _SUB_PROC_SUFFIX):
        return None
    # 3) 화이트리스트 정확 토큰 → 정규화
    for token, canon in _SUB_WHITELIST:
        if token in n:
            return canon
    return None


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


INGREDIENT_REGION_MAP = {
    # 쌀
    '이천 쌀': '경기도 이천', '여주 쌀': '경기도 여주',
    '철원 쌀': '강원도 철원', '김제 쌀': '전라북도 김제',
    '안동 쌀': '경상북도 안동', '홍성 쌀': '충청남도 홍성',
    '진주 쌀': '경상남도 진주', '나주 쌀': '전라남도 나주',
    # 과일
    '제주 감귤': '제주도', '감귤': '제주도', '한라봉': '제주도',
    '청송 사과': '경상북도 청송', '사과': '경상북도 청송',
    '나주 배': '전라남도 나주', '배': '전라남도 나주',
    '논산 딸기': '충청남도 논산', '딸기': '충청남도 논산',
    '영천 포도': '경상북도 영천', '포도': '경상북도 영천',
    '황도': '경상북도 청도', '복숭아': '경기도 이천',
    # 기타 재료
    '해남 고구마': '전라남도 해남', '고구마': '전라남도 해남',
    '가평 잣': '경기도 가평', '잣': '경기도 가평',
    '강화 인삼': '인천 강화', '풍기 인삼': '경상북도 영주',
    '인삼': '충청남도 금산', '홍삼': '충청남도 금산',
    '보성 녹차': '전라남도 보성', '녹차': '전라남도 보성',
    '담양 대나무': '전라남도 담양',
    '영광 모싯잎': '전라남도 영광',
    # 기본값
    '쌀': '경기도 이천',
}


class RecipeAI:
    """레시피 AI 클라이언트"""

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    def get_region_from_ingredient(self, main_ingredient: str) -> list:
        """
        메인재료 → 생산 지역 목록 반환.
        1순위: 농사로 지역특산물 수집 데이터(data/ingredient_region_map.json),
        2순위(fallback): 하드코딩 테이블.
        """
        if not main_ingredient or not main_ingredient.strip():
            return []  # 빈 입력은 substring 오매칭 방지
        if _has_rice_text(main_ingredient):
            return []

        # 1순위: 농사로 수집 데이터
        nongsaro = _match_nongsaro_regions(main_ingredient)
        if nongsaro:
            return nongsaro

        # 2순위: 하드코딩 fallback
        _MAP = {
            '이천 쌀': ['경기도 이천'],
            '여주 쌀': ['경기도 여주'],
            '철원 쌀': ['강원도 철원'],
            '김제 쌀': ['전라북도 김제'],
            '안동 쌀': ['경상북도 안동'],
            '홍성 쌀': ['충청남도 홍성'],
            '쌀': ['경기도 이천', '강원도 철원', '전라북도 김제'],
            '감귤': ['제주도'],
            '한라봉': ['제주도'],
            '사과': ['경상북도 청송', '충청북도 충주', '경상남도 거창'],
            '배': ['전라남도 나주', '충청남도 천안'],
            '딸기': ['충청남도 논산', '경상남도 진주'],
            '포도': ['경상북도 영천', '충청북도 영동'],
            '복숭아': ['경기도 이천', '충청북도 음성'],
            '고구마': ['전라남도 해남', '충청남도 당진'],
            '잣': ['경기도 가평'],
            '인삼': ['충청남도 금산', '경상북도 영주'],
            '녹차': ['전라남도 보성'],
            '대나무': ['전라남도 담양'],
        }
        if main_ingredient in _MAP:
            return _MAP[main_ingredient]
        for key, regions in _MAP.items():
            if key in main_ingredient or main_ingredient in key:
                return regions
        return []

    async def suggest_sub_ingredients(self, main_ingredient: str, region: Optional[str] = None) -> Dict:
        """
        서브재료 추천

        Args:
            main_ingredient: 메인 재료
            region: 지역

        Returns:
            서브재료 리스트
        """
        if not region:
            return {
                "sub_ingredients": [],
                "region": None,
                "data_source": "unavailable",
                "traditional_liquor_status": "NEEDS_REVIEW",
                "warnings": ["region을 입력해야 지역 특산물 후보를 확인할 수 있습니다."],
            }

        candidates: List[str] = []
        for product in _load_local_products():
            area = str(product.get("area") or "").strip()
            if not _region_matches(area, region):
                continue
            canon = _normalize_sub_ingredient(product.get("name"))   # 화이트리스트 필터 + 정규화
            if not canon or canon == main_ingredient or canon in candidates:
                continue
            candidates.append(canon)
        if candidates:
            # 후보가 2개 이상일 때만 Gemini 선별(보조 단계). 실패 시 기존대로 candidates[:5] 폴백.
            selected = candidates[:5]
            if len(candidates) >= 2 and self.gemini_api_key:
                try:
                    selected = await self._gemini_select_sub_ingredients(main_ingredient, candidates)
                except Exception as exc:
                    logger.warning("서브재료 Gemini 선별 실패 → 후보 그대로 사용: %s", type(exc).__name__)
                    selected = candidates[:5]
            return {
                "sub_ingredients": selected,
                "region": region,
                "data_source": "nongsaro_api",
                "traditional_liquor_status": "NEEDS_REVIEW",
                "warnings": ["지역특산주 요건 충족 여부는 별도 법률·면허 검토가 필요합니다."],
            }

        manual = [
            ingredient
            for ingredient, mapped_region in INGREDIENT_REGION_MAP.items()
            if region in mapped_region
            and ingredient != main_ingredient
            and not _has_rice_text(ingredient)
            and not any(k in ingredient for k in _SUB_BASE_EXCLUDE)   # 쌀·찹쌀·현미·보리 키 제외
        ]
        if manual:
            return {
                "sub_ingredients": _filter_rice_sub_ingredients(manual[:5]),
                "region": region,
                "data_source": "manual",
                "traditional_liquor_status": "NEEDS_REVIEW",
                "warnings": ["수동 매핑 기반 후보이며 실제 생산·지역특산주 요건 확인이 필요합니다."],
            }

        return {
            "sub_ingredients": [],
            "region": region,
            "data_source": "unavailable",
            "traditional_liquor_status": "NEEDS_REVIEW",
            "warnings": ["해당 지역에서 확인된 특산물 후보가 없습니다."],
        }

    async def _gemini_select_sub_ingredients(self, main_ingredient: str, candidates: List[str]) -> List[str]:
        """지역 후보 중 main_ingredient 와 궁합 좋은 서브재료를 Gemini 로 선별.

        - 반드시 candidates 안에서만 고른다(목록에 없는 재료 생성 금지).
        - 실패/파싱오류 시 예외를 그대로 올려 호출자가 candidates[:5] 로 폴백하게 한다.
        """
        import google.genai as genai
        import re

        client = genai.Client(api_key=self.gemini_api_key)
        candidates_str = ", ".join(candidates)
        prompt = (
            f"'{main_ingredient}'(으)로 만드는 막걸리·전통주에 어울리는 서브재료를 아래 후보 중에서만 골라줘.\n"
            f"후보: {candidates_str}\n"
            "막걸리·전통주에 잘 어울리는 재료만 무난히 어울리는 것 위주로 3~5개 골라줘. "
            "채소·나물·가공식품·비식품·판매처/상품명은 절대 고르지 마라.\n"
            "반드시 위 후보 목록 안에 있는 재료만 사용하고, 목록에 없는 재료는 만들지 마.\n"
            "재료 이름 문자열만 담은 JSON 배열로만 답변. 이유·점수 등 다른 정보는 넣지 마."
        )

        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config={"max_output_tokens": 200},
        )
        result_text = response.text
        json_match = re.search(r'\[[\s\S]*\]', result_text)
        if json_match:
            result_text = json_match.group(0)
        parsed = json.loads(result_text)
        if not isinstance(parsed, list):
            raise ValueError("Gemini 서브재료 응답이 배열이 아님")

        # 후보 목록 안의 재료만, 순서 유지·중복 제거
        allowed = set(candidates)
        selected: List[str] = []
        for item in parsed:
            name = str(item).strip()
            if name in allowed and name not in selected:
                selected.append(name)
        if not selected:
            raise ValueError("Gemini 선별 결과가 후보와 일치하지 않음")
        return _filter_rice_sub_ingredients(selected[:5])

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
                "전통주 양조 전문가. 아래 레시피 제작 가능성을 JSON으로만 반환.\n"
                '{"feasibility":"high/medium/low","score":0~100,'
                '"issues":["문제점"],"suggestions":["개선안"],"summary":"한줄결과"}\n\n'
                f"제목:{title} 메인:{main_ingredient} 서브:{sub_str} "
                f"도수:{abv_range} 맛:{tags_str}"
            )

            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt,
                config={"max_output_tokens": 200}
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
