"""
국가법령정보센터 API 클라이언트
전통주 관련 법령 실시간 조회 및 콘텐츠 필터링
"""

import asyncio
import logging
import os
import json
import hashlib

# Gemini 에러 관련 상수
_QUOTA_MSG = "현재 AI 서비스가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요."
_CONN_MSG  = "AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."


def _is_quota_error(e: Exception) -> bool:
    s = str(e)
    return '429' in s or 'quota exceeded' in s.lower() or 'resource_exhausted' in s.lower()


def _gemini_error_message(e: Exception) -> str:
    return _QUOTA_MSG if _is_quota_error(e) else _CONN_MSG
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentType(Enum):
    """콘텐츠 타입"""
    RECIPE = "recipe"
    FUNDING = "funding"


class ViolationCategory(Enum):
    """위반 카테고리"""
    MINOR_TARGET = "미성년자 타겟"
    ILLEGAL_INGREDIENTS = "불법/금지 재료"
    REGIONAL_REQUIREMENTS = "지역특산주 요건 불충족"
    FALSE_ADVERTISING = "과대광고/허위표시"
    UNLICENSED_MANUFACTURING = "무허가 제조 방법"
    UNREALISTIC_ABV = "도수 표기 비현실적"
    TRADEMARK_INFRINGEMENT = "상표명 침해 가능성"
    FUNDING_REGULATION = "펀딩 금융 규제 위반"


@dataclass
class LawInfo:
    """법령 정보"""
    name: str
    law_id: str
    keywords: List[str]
    description: str


@dataclass
class Article:
    """조문 정보"""
    article_id: str
    article_name: str
    content: str
    law_name: str


@dataclass
class ViolationDetail:
    """위반 상세 정보"""
    category: str
    law: str
    reason: str
    article: Optional[str] = None


@dataclass
class FilterResult:
    """필터링 결과

    verdict: 3등급 판정
      - "block"  : 명백한 위반 → 자동 차단
      - "pass"   : 명백한 정상 → 자동 통과
      - "review" : 애매 → 관리자 검토 큐로 (자동 차단/통과 안 함)
    violation: 하위호환용 bool. block일 때만 True (review/pass는 False → 자동 차단 안 됨).
    """
    violation: bool
    details: List[ViolationDetail]
    recommendation: str
    verdict: str = "pass"


class LawClient:
    """국가법령정보센터 API 클라이언트"""

    # 법령 목록
    LAWS: Dict[str, LawInfo] = {
        "청소년보호법": LawInfo(
            name="청소년보호법",
            law_id="청소년보호법",
            keywords=["청소년", "미성년자", "19세 미만", "18세 미만", "미성년", "학생", "청소년 판매", "미성년자 판매"],
            description="청소년보호법 제28조: 만 19세 미만 청소년에게 주류 판매·제공 금지. 위반 시 2년 이하 징역 또는 2천만원 이하 벌금. 온라인 주류 판매 시 성인 인증 의무화. '청소년용', '청소년에게 좋은' 등 청소년 대상 표현 금지."
        ),
        "식품위생법": LawInfo(
            name="식품위생법",
            law_id="식품위생법",
            keywords=["식품", "위생", "유해물질", "금지 재료", "첨가물", "표시", "광고", "허위", "과대광고"],
            description="식품위생법 제13조: 식품의 허위·과대광고 금지. 주류의 건강 기능성(숙취 해소, 피로 회복, 다이어트, 간 건강, 면역력 증진 등) 효능 광고 금지. 의약품으로 오인할 수 있는 표현 사용 불가. 위반 시 5년 이하 징역 또는 5천만원 이하 벌금."
        ),
        "전통주등의산업진흥에관한법률": LawInfo(
            name="전통주등의산업진흥에관한법률",
            law_id="전통주등의산업진흥에관한법률",
            keywords=["전통주", "지역특산주", "요건", "인증", "제조", "양조", "누룩", "쌀"],
            description="전통주 등의 산업진흥에 관한 법률: 지역 특산주는 해당 지역 농산물을 주원료로 사용해야 함. 지역 농산물 사용 비율 기준 준수 필요. 전통주 지리적 표시제 준수. 원산지 허위 표시 금지."
        ),
        "표시광고법": LawInfo(
            name="표시광고의공정화에관한법률",
            law_id="표시광고의공정화에관한법률",
            keywords=["표시", "광고", "허위", "과대", "기만", "오인", "소비자"],
            description="표시광고의공정화에관한법률 제3조: 거짓·과장 광고, 기만적 광고, 부당 비교 광고, 비방 광고 금지. 소비자를 오인시킬 수 있는 효능·효과 주장 시 객관적 근거 필수. 위반 시 시정명령 및 과징금 부과."
        ),
        "주세법": LawInfo(
            name="주세법",
            law_id="주세법",
            keywords=["주세", "주류", "제조", "면허", "도수", "알코올", "양조", "발효"],
            description="주세법 제3조: 주류 제조 면허 없이 주류 제조 금지. 제9조: 제조장 외 장소에서 주류 제조 불가. 탁주·약주·청주·맥주·과실주·증류주 등 주종별 제조 기준 준수 의무. 위반 시 면허 취소 및 형사처벌."
        ),
        "상표법": LawInfo(
            name="상표법",
            law_id="상표법",
            keywords=["상표", "브랜드", "명칭", "침해", "유사", "등록"],
            description="상표권 보호 및 침해 방지 규정"
        ),
        "자본시장법": LawInfo(
            name="자본시장과금융투자업에관한법률",
            law_id="자본시장과금융투자업에관한법률",
            keywords=["투자", "펀딩", "수익", "원금", "보장", "금융", "증권"],
            description="주류 면허 등에 관한 법률: 주류 판매업 면허 없이 주류 판매 금지. 전통주에 한해 온라인 통신판매 허용. 판매 시 성인 인증 필수. 구매자 연령 확인 의무. 미성년자 대리 구매 방지 조치 필요. 투자 관련: 수익 보장·원금 보장 표현 금지, 위반 시 자본시장법 제178조 위반."
        ),
        "저작권법": LawInfo(
            name="저작권법",
            law_id="저작권법",
            keywords=["저작권", "레시피", "방법", "침해", "복제", "배포"],
            description="저작권 보호 및 침해 방지 규정"
        ),
        "전자상거래법": LawInfo(
            name="전자상거래등에서의소비자보호에관한법률",
            law_id="전자상거래등에서의소비자보호에관한법률",
            keywords=["전자상거래", "성인인증", "연령확인", "주류", "판매"],
            description="전자상거래에서의 소비자 보호 규정"
        )
    }

    # 위반 키워드 매핑
    VIOLATION_KEYWORDS: Dict[ViolationCategory, Dict[str, List[str]]] = {
        ViolationCategory.MINOR_TARGET: {
            "keywords": ["청소년", "미성년자", "19세 미만", "18세 미만", "미성년", "학생", "학교", "청소년용", "미성년자용", "어린이", "아이", "유아", "초등학생", "중학생", "고등학생"],
            "laws": ["청소년보호법"]
        },
        ViolationCategory.ILLEGAL_INGREDIENTS: {
            "keywords": ["메탄올", "공업용", "독성", "유해물질", "금지 재료", "불법 첨가물"],
            "laws": ["식품위생법"]
        },
        ViolationCategory.REGIONAL_REQUIREMENTS: {
            "keywords": ["지역특산주", "전통주 인증", "지역 재료", "100% 지역", "지역 특산"],
            "laws": ["전통주등의산업진흥에관한법률"]
        },
        ViolationCategory.FALSE_ADVERTISING: {
            # NOTE: 단독 "약"은 '약주'(정상 주종)·'약재'(정상 재료)에 오매칭하므로 제외.
            #       효능 맥락은 "약효"/"의약"/"치료제"로 한정해 트리거.
            "keywords": ["숙취 없는", "숙취 해소", "숙취가 없는", "숙취가", "숙취없는", "숙취해소", "건강에 좋은", "치료", "약효", "효능", "100% 안전", "부작용 없는", "숙콤 없는", "숙취방지", "숙취예방", "해독", "간 보호", "간 건강", "의약", "치료제", "완치", "완벽한", "무조건", "반드시", "확실한", "다이어트", "피로 회복", "피로회복", "면역력", "디톡스"],
            "laws": ["식품위생법", "표시광고법"]
        },
        ViolationCategory.UNLICENSED_MANUFACTURING: {
            "keywords": ["가정 양조", "무허가", "면허 없이", "자가 제조", "집에서 만드는"],
            "laws": ["주세법"]
        },
        ViolationCategory.UNREALISTIC_ABV: {
            "keywords": ["도수 0%", "알코올 없는", "무알콜", "도수 100%"],
            "laws": ["주세법"]
        },
        ViolationCategory.TRADEMARK_INFRINGEMENT: {
            "keywords": ["유사 브랜드", "모방", "짝퉁", "카피"],
            "laws": ["상표법"]
        },
        ViolationCategory.FUNDING_REGULATION: {
            "keywords": ["수익 보장", "원금 보장", "확정 수익", "무위험", "100% 수익"],
            "laws": ["자본시장법"]
        }
    }

    # 빠른 키워드 감지용 (Gemini 호출 전 1차 필터링)
    QUICK_VIOLATION_KEYWORDS = {
        "청소년보호법": ["미성년자", "어린이", "청소년", "아동", "초등학생", "중학생", "고등학생"],
        "식품위생법": ["숙취없는", "숙취 없는", "건강에 좋은", "치료효과", "치료 효과", "의약"],
        "자본시장법": ["원금보장", "수익보장"]
    }

    def __init__(self):
        self.law_api_key = os.getenv("LAW_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        from app.law_rag import LawRAG
        self.law_rag = LawRAG()

        # API 엔드포인트
        self.law_api_url = "https://www.law.go.kr/DRF/lawSearch.do"
        self.law_detail_url = "https://www.law.go.kr/DRF/lawService.do"

        # 법제처 OPEN API 호출 헤더 (브라우저 UA/Referer, 환경변수로 override 가능)
        self.law_headers = {
            "User-Agent": os.getenv(
                "LAW_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ),
            "Referer": os.getenv("LAW_REFERER", "https://www.law.go.kr/"),
        }

        # 캐시 디렉토리
        self.cache_dir = Path("cache/law")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 캐시 만료 시간 (24시간)
        self.cache_expiry = timedelta(hours=24)

    def _get_cache_key(self, law_name: str, keywords: List[str]) -> str:
        """캐시 키 생성"""
        key_str = f"{law_name}:{','.join(sorted(keywords))}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """캐시 파일 경로 생성"""
        return self.cache_dir / f"{cache_key}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """캐시 유효성 확인"""
        if not cache_path.exists():
            return False

        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return datetime.now() - file_time < self.cache_expiry

    def _load_from_cache(self, cache_key: str) -> Optional[List[Article]]:
        """캐시에서 로드"""
        cache_path = self._get_cache_path(cache_key)

        if not self._is_cache_valid(cache_path):
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            articles = [Article(**item) for item in data]
            logger.info(f"캐시 로드: {cache_key}")
            return articles

        except Exception as e:
            logger.error(f"캐시 로드 실패: {e}")
            return None

    def _save_to_cache(self, cache_key: str, articles: List[Article]):
        """캐시에 저장"""
        cache_path = self._get_cache_path(cache_key)

        try:
            data = [asdict(article) for article in articles]
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"캐시 저장: {cache_key}")

        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")

    async def get_relevant_articles(self, law_name: str, keywords: List[str]) -> List[Article]:
        """
        국가법령정보센터 API로 관련 조문 실시간 조회

        Args:
            law_name: 법령 이름
            keywords: 검색 키워드

        Returns:
            관련 조문 리스트
        """
        if not self.law_api_key:
            logger.warning("LAW_API_KEY가 설정되지 않음")
            return []

        # 캐시 확인
        cache_key = self._get_cache_key(law_name, keywords)
        cached_articles = self._load_from_cache(cache_key)

        if cached_articles:
            return cached_articles

        try:
            # API 호출
            params = {
                "OC": self.law_api_key,
                "target": "law",
                "query": f"{law_name} {' '.join(keywords)}",
                "type": "JSON",
                "display": 10
            }

            async with httpx.AsyncClient(timeout=10.0, headers=self.law_headers) as client:
                response = await client.get(self.law_api_url, params=params)
                response.raise_for_status()

                data = response.json()

                # 조문 추출 (응답구조: LawSearch.law[] → lawService.do?MST → 법령.조문.조문단위[])
                articles = []
                law_list = data.get("LawSearch", {}).get("law", [])
                if isinstance(law_list, dict):
                    law_list = [law_list]
                for law in law_list[:1]:  # 최상위 1건만 상세 조회 (rate limit 배려)
                    mst = law.get("법령일련번호") or law.get("법령ID", "")
                    detail_params = {
                        "OC": self.law_api_key,
                        "target": "law",
                        "type": "JSON",
                        "MST": mst,
                    }
                    try:
                        detail_response = await client.get(self.law_detail_url, params=detail_params)
                        detail_response.raise_for_status()
                        detail_data = detail_response.json()

                        units = detail_data.get("법령", {}).get("조문", {}).get("조문단위", [])
                        if isinstance(units, dict):
                            units = [units]
                        for art in units:
                            if art.get("조문여부") != "조문":
                                continue
                            content = (art.get("조문내용") or "").strip()
                            if not content:
                                continue
                            articles.append(Article(
                                article_id=str(art.get("조문번호", "")),
                                article_name=(art.get("조문제목") or "").strip(),
                                content=content,
                                law_name=law_name
                            ))
                    except Exception as e:
                        logger.warning(f"상세 정보 조회 실패: {e}")

                # 캐시 저장
                if articles:
                    self._save_to_cache(cache_key, articles)

                logger.info(f"조문 조회 완료: {law_name}, {len(articles)}개")
                return articles

        except Exception as e:
            logger.error(f"조문 조회 실패: {e}")
            return []

    def _check_violation_keywords(self, text: str, category: ViolationCategory) -> bool:
        """위반 키워드 확인"""
        if not text:
            return False

        text_lower = text.lower()
        keywords = self.VIOLATION_KEYWORDS[category]["keywords"]

        return any(keyword in text_lower for keyword in keywords)

    # 정상 주종/재료 용어 (그 자체로 위반 아님 — Gemini 혼동 방지용)
    NORMAL_LIQUOR_TERMS = ["약주", "청주", "탁주", "막걸리", "소주", "증류주", "과실주", "약재", "누룩"]

    # Gemini 호출 타임아웃(초)
    GEMINI_TIMEOUT_SEC = 25.0

    async def _analyze_with_gemini(
        self,
        title: str,
        description: str,
        ingredients: str,
        articles: List[Article],
        content_type: ContentType
    ) -> dict:
        """
        Gemini API로 콘텐츠를 3등급(block/pass/review) 판정.

        Returns:
            {"verdict": "block"|"pass"|"review"|"error",
             "violations": List[ViolationDetail],
             "recommendation": str}
            - "error": API 키 없음/타임아웃/호출 실패 → 호출부에서 키워드 fallback 적용.
        """
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY가 설정되지 않음")
            return {"verdict": "error", "violations": [], "recommendation": "AI 미설정"}

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-2.5-flash-lite')

            # 조문 정보를 텍스트로 변환
            articles_text = "\n".join([
                f"- {article.law_name} {article.article_name}: {article.content[:200]}..."
                for article in articles[:5]
            ]) or "(관련 조문 검색 결과 없음)"

            normal_terms = ", ".join(self.NORMAL_LIQUOR_TERMS)

            prompt = f"""
당신은 전통주 관련 법률 전문가입니다. 아래 콘텐츠를 3등급으로 판정하세요.

**판정 등급(verdict):**
- "block" : 법 위반이 명백한 경우. (예: 미성년자/청소년 대상 표현, 질병 예방·치료·효능 표방(숙취 해소·다이어트·면역력·피로 회복·간 건강 등), 원금/수익 보장)
- "pass"  : 명백히 정상인 경우. (단순 맛·향·원료·산지·제조방식 표현, 정상 주종명 사용)
- "review": 위반 소지는 있으나 명백하지 않아 사람(관리자) 검토가 필요한 경우. (효능을 직접 말하진 않지만 암시하는 표현 등)

**중요 원칙:**
1. 애매하면 절대 block 하지 말고 "review"로 보내세요. block은 명백한 위반에만.
2. 다음 용어는 정상 전통주의 주종/재료 명칭이며 그 자체로는 위반이 아닙니다: {normal_terms}.
   특히 "약주"의 '약', "청주"는 정상 술 이름입니다. "청주"를 "청소년"으로 혼동하지 마세요. '약재'는 정상 재료입니다.
3. 판단 근거는 **입력 콘텐츠에 실제로 존재하는 문구만** 인용하세요. 입력에 없는 단어를 지어내지 마세요(환각 금지).
4. 효능·기능성을 직접 단정하면 block, 은근히 암시하는 정도면 review.

**펀딩 콘텐츠(content_type=funding) 판정 기준:**
A. 전통주 제조·판매를 위한 **리워드형 펀딩(후원 대가로 제품/굿즈 제공)은 정상(pass)**입니다.
   '펀딩', '후원', '공동구매'라는 단어 자체는 위반이 아닙니다.
B. 펀딩이 block인 경우는 **원금 보장 / 수익(이자·배당) 보장 / 확정 투자수익 약속 / 무위험 수익**을
   **긍정적으로 약속**할 때뿐입니다. (예: "원금 보장", "연 N% 수익 확정", "무위험 고수익")
C. ★중요: "수익을 보장하지 않음", "원금 손실 위험이 있음" 같은 **위험 고지·부정 표현은 위반이 아니라
   오히려 정상(컴플라이언스 양성 신호)**입니다. 이런 고지·부정 문구를 위반 근거로 인용하지 마세요.
D. 수익을 명시 보장하진 않으나 은근히 암시하는 경우("높은 수익률 기대" 등)는 review.

**분석 대상 콘텐츠:**
제목: {title}
설명: {description}
재료: {ingredients}
콘텐츠 타입: {content_type.value}

**관련 법령 조문(참고용):**
{articles_text}

**Few-shot 예시 (각 예시의 law/reason은 실제 근거 법령에 연결 — 같은 유형이면 동일 법령을 인용):**
- 제목 "숙취 없는 막걸리" 또는 "다음날 개운한 막걸리" → {{"verdict":"block","category":"과대광고/효능표방","law":"식품 등의 표시·광고에 관한 법률 §8","reason":"숙취 해소·다음날 개운함 등 신체 효능을 표방(질병·생리활성 암시). 식약처가 다수 단속하는 숙취해소 표방 유형"}}
- 제목 "간 건강에 좋은 막걸리"·"면역력 높이는 약주"·"다이어트 막걸리"·"피로 회복 막걸리" → {{"verdict":"block","category":"과대광고/효능표방","law":"식품 등의 표시·광고에 관한 법률 §8","reason":"간 건강·면역력·다이어트·피로회복 등 의약품 오인 또는 질병 예방·치료 효능 표방. 식약처 핵심 단속 유형"}}
- 제목 "청소년도 즐기는 전통주" 또는 "학생 추천 막걸리" → {{"verdict":"block","category":"청소년 음주 조장","law":"청소년보호법","reason":"청소년·학생 대상 음주 권유·조장 표현(주류는 청소년유해약물). ※'청주'는 정상 주종명이니 '청소년'과 혼동 금지"}}
- 제목 "취하지 않는 순한 술" 또는 "부담없이 많이 마시는 막걸리" → {{"verdict":"block","category":"과음 조장","law":"국민건강증진법 §8의2","reason":"'취하지 않는다'·'많이 마셔도 됨' 등 과음을 조장·정당화하는 표현(주류광고 준수사항 위반 소지)"}}
- 제목 "원금 보장 막걸리 펀딩" 설명 "확정 수익" → {{"verdict":"block","category":"펀딩 금융 규제","law":"자본시장법","reason":"원금·확정 투자수익 보장 약속(투자수익 보장 금지). ※리워드형 펀딩 자체는 정상"}}
- 제목 "전통 방식으로 빚은 깔끔한 막걸리" → {{"verdict":"pass","category":"","law":"","reason":"제조방식·맛 표현일 뿐 효능·연령·투자 요소 없음 — 정상"}}
- 제목 "정직한 약주 리워드 펀딩" 설명 "수익을 보장하지 않으며 원금 손실 위험이 있습니다" → {{"verdict":"pass","category":"","law":"","reason":"위험 고지·부정 표현은 컴플라이언스 양성 신호 — 위반 근거로 인용 금지(자본시장법상 정상)"}}
- 제목 "건강한 재료로 만든 막걸리" → {{"verdict":"review","category":"과대광고 소지","law":"식품 등의 표시·광고에 관한 법률 §8","reason":"'건강한 재료'가 재료 설명인지 신체 효능 암시인지 모호 — 자동 차단 말고 관리자 검토"}}

**답변 형식 (JSON만 반환, 다른 텍스트 없음):**
{{
  "verdict": "block" 또는 "pass" 또는 "review",
  "violations": [
    {{"category": "분류", "law": "관련 법령", "reason": "근거(입력 문구 인용)", "article": "조문 번호(있으면)"}}
  ],
  "recommendation": "수정 권장사항 또는 검토 사유"
}}
verdict가 "pass"면 violations는 빈 배열로 두세요.
"""

            response = await asyncio.wait_for(
                model.generate_content_async(prompt),
                timeout=self.GEMINI_TIMEOUT_SEC,
            )
            result_text = response.text

            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', result_text)
                if json_match:
                    result_text = json_match.group(0)

                result = json.loads(result_text)

                verdict = str(result.get("verdict", "")).lower().strip()
                if verdict not in ("block", "pass", "review"):
                    # 구버전 호환: violation bool이 오면 매핑
                    if "violation" in result:
                        verdict = "block" if result.get("violation") else "pass"
                    else:
                        verdict = "review"  # 알 수 없는 값 → 보수적으로 검토

                violations = []
                if verdict in ("block", "review"):
                    for v in result.get("violations", []):
                        violations.append(ViolationDetail(
                            category=v.get("category", ""),
                            law=v.get("law", ""),
                            reason=v.get("reason", ""),
                            article=v.get("article")
                        ))

                recommendation = result.get("recommendation", "")
                return {"verdict": verdict, "violations": violations,
                        "recommendation": recommendation}

            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                logger.error(f"원본 응답: {result_text}")
                # 파싱 실패 → 자동 차단 대신 관리자 검토로 (보수적이되 통과는 막음)
                return {"verdict": "review", "violations": [ViolationDetail(
                    category="파싱오류", law="알 수 없음",
                    reason="AI 응답 파싱 실패 — 관리자 검토 필요", article="")],
                    "recommendation": "AI 응답 형식 오류로 관리자 검토가 필요합니다."}

        except asyncio.TimeoutError:
            logger.error(f"Gemini 타임아웃({self.GEMINI_TIMEOUT_SEC}s)")
            return {"verdict": "error", "violations": [], "recommendation": "AI 응답 시간 초과"}
        except Exception as e:
            msg = _gemini_error_message(e)
            logger.error(f"Gemini 분석 실패: {e}")
            return {"verdict": "error", "violations": [], "recommendation": msg}

    async def filter_content(
        self,
        title: str,
        description: str,
        ingredients: str,
        content_type: ContentType = ContentType.RECIPE
    ) -> FilterResult:
        """
        콘텐츠 필터링 (MVP 1차 4개 항목 자동 검토)

        Args:
            title: 제목
            description: 설명
            ingredients: 재료
            content_type: 콘텐츠 타입 (recipe 또는 funding)

        Returns:
            필터링 결과
        """
        logger.info(f"콘텐츠 필터링 시작: {title}")

        # ── 1단계: 빠른 키워드 즉시차단 (명백 위반은 Gemini 전에 거름) ──
        text = (title + " " + description).replace(" ", "")
        for law, keywords in self.QUICK_VIOLATION_KEYWORDS.items():
            for kw in keywords:
                if kw.replace(" ", "") in text:
                    logger.info(f"위반 키워드 감지: {kw} ({law})")
                    return FilterResult(
                        violation=True,
                        verdict="block",
                        details=[ViolationDetail(
                            category="키워드감지",
                            law=law,
                            reason=f"위반 키워드 감지: {kw}"
                        )],
                        recommendation=f"'{kw}' 표현을 수정해주세요"
                    )

        # ── 2단계: RAG로 관련 조문 검색 (키워드 일치 여부와 무관하게 항상) ──
        query = f"{title} {description}"
        rag_results = self.law_rag.search(query, top_k=3)
        rag_articles = [
            Article(
                article_id=f"rag_{i}",
                article_name="RAG 검색 결과",
                content=result['content'],
                law_name=result['law_name']
            )
            for i, result in enumerate(rag_results)
        ]
        if rag_articles:
            logger.info(f"RAG 검색 완료: {len(rag_articles)}개 법령 컨텍스트 확보")

        # ── 3단계: 모든 콘텐츠를 Gemini로 1회 검토 (게이트 제거, 0_auto_pass 경로 없음) ──
        analysis = await self._analyze_with_gemini(
            title, description, ingredients, rag_articles, content_type
        )
        verdict = analysis["verdict"]

        # ── Gemini 실패 fallback: 키워드 결과라도 사용, 불확실하면 review(보류) ──
        if verdict == "error":
            full_text = f"{title} {description} {ingredients}"
            fb_violations = self._keyword_fallback_violations(full_text, content_type)
            if fb_violations:
                logger.info("Gemini 실패 → 키워드 fallback: 위반 키워드 발견 → block")
                return FilterResult(
                    violation=True, verdict="block", details=fb_violations,
                    recommendation="AI 검토 실패. 키워드 기반으로 차단: "
                                    + ", ".join(v.reason for v in fb_violations),
                )
            logger.info("Gemini 실패 → 키워드 fallback: 위반 키워드 없음 → review(보류)")
            return FilterResult(
                violation=False, verdict="review",
                details=[ViolationDetail(category="검토보류", law="",
                         reason=analysis.get("recommendation") or "AI 검토 실패")],
                recommendation="AI 검토에 실패하여 관리자 검토 보류로 분류했습니다.",
            )

        # ── 정상 판정 매핑 ──
        violations = analysis["violations"]
        if verdict == "block":
            recommendation = analysis.get("recommendation") or (
                "다음 문제를 수정해주세요: " + ", ".join(v.reason for v in violations))
        elif verdict == "review":
            recommendation = analysis.get("recommendation") or "관리자 검토가 필요합니다."
        else:  # pass
            recommendation = analysis.get("recommendation") or "법적 문제가 없습니다."

        result = FilterResult(
            violation=(verdict == "block"),
            verdict=verdict,
            details=violations,
            recommendation=recommendation,
        )

        logger.info(f"필터링 완료: verdict={verdict}, 위반항목={len(violations)}")
        return result

    def _keyword_fallback_violations(
        self, full_text: str, content_type: ContentType
    ) -> List[ViolationDetail]:
        """Gemini 실패 시 키워드 기반 위반 탐지 (기존 동작 보존용 fallback)."""
        categories = [
            ViolationCategory.MINOR_TARGET,
            ViolationCategory.ILLEGAL_INGREDIENTS,
            ViolationCategory.REGIONAL_REQUIREMENTS,
            ViolationCategory.FALSE_ADVERTISING,
        ]
        if content_type == ContentType.FUNDING:
            categories += [
                ViolationCategory.UNLICENSED_MANUFACTURING,
                ViolationCategory.UNREALISTIC_ABV,
                ViolationCategory.TRADEMARK_INFRINGEMENT,
                ViolationCategory.FUNDING_REGULATION,
            ]
        violations = []
        for category in categories:
            if self._check_violation_keywords(full_text, category):
                laws = self.VIOLATION_KEYWORDS[category]["laws"]
                violations.append(ViolationDetail(
                    category=category.value,
                    law=", ".join(laws),
                    reason=f"키워드 기반 {category.value} 의심 (AI 검토 실패)",
                ))
        return violations

    def get_law_info(self, law_name: str) -> Optional[LawInfo]:
        """
        법령 정보 조회

        Args:
            law_name: 법령 이름

        Returns:
            법령 정보
        """
        return self.LAWS.get(law_name)

    def get_all_laws(self) -> List[LawInfo]:
        """모든 법령 정보 조회"""
        return list(self.LAWS.values())


def main():
    """메인 실행 함수"""
    import asyncio

    client = LawClient()

    print("=== 국가법령정보센터 API 클라이언트 테스트 ===\n")

    # 1. 법령 정보 확인
    print("--- 1. 법령 정보 ---")
    for law_name, law_info in client.LAWS.items():
        print(f"{law_name}: {law_info.description}")

    # 2. 콘텐츠 필터링 테스트
    print("\n--- 2. 콘텐츠 필터링 테스트 ---")

    # 테스트 케이스 1: 정상 콘텐츠
    print("\n[테스트 1: 정상 콘텐츠]")
    result = asyncio.run(client.filter_content(
        title="전통 막걸리 레시피",
        description="쌀과 누룩으로 만드는 전통 막걸리 제조 방법",
        ingredients="쌀, 누룩, 물",
        content_type=ContentType.RECIPE
    ))
    print(f"위반 여부: {result.violation}")
    print(f"권장사항: {result.recommendation}")

    # 테스트 케이스 2: 미성년자 타겟
    print("\n[테스트 2: 미성년자 타겟]")
    result = asyncio.run(client.filter_content(
        title="청소년을 위한 막걸리",
        description="학생들이 즐길 수 있는 맛있는 막걸리",
        ingredients="쌀, 누룩, 물",
        content_type=ContentType.RECIPE
    ))
    print(f"위반 여부: {result.violation}")
    print(f"권장사항: {result.recommendation}")

    # 테스트 케이스 3: 과대광고
    print("\n[테스트 3: 과대광고]")
    result = asyncio.run(client.filter_content(
        title="숙취 없는 건강 막걸리",
        description="숙취가 전혀 없고 건강에 좋은 막걸리",
        ingredients="쌀, 누룩, 물",
        content_type=ContentType.RECIPE
    ))
    print(f"위반 여부: {result.violation}")
    print(f"권장사항: {result.recommendation}")

    # 테스트 케이스 4: 펀딩 금융 규제
    print("\n[테스트 4: 펀딩 금융 규제]")
    result = asyncio.run(client.filter_content(
        title="100% 수익 보장 막걸리 펀딩",
        description="투자하면 원금 보장 100% 수익",
        ingredients="쌀, 누룩, 물",
        content_type=ContentType.FUNDING
    ))
    print(f"위반 여부: {result.violation}")
    print(f"권장사항: {result.recommendation}")


if __name__ == "__main__":
    main()
