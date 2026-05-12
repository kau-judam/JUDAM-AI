"""
국가법령정보센터 API 클라이언트
전통주 관련 법령 실시간 조회 및 콘텐츠 필터링
"""

import logging
import os
import json
import hashlib
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
    """필터링 결과"""
    violation: bool
    details: List[ViolationDetail]
    recommendation: str


class LawClient:
    """국가법령정보센터 API 클라이언트"""

    # 법령 목록
    LAWS: Dict[str, LawInfo] = {
        "청소년보호법": LawInfo(
            name="청소년보호법",
            law_id="청소년보호법",
            keywords=["청소년", "미성년자", "19세 미만", "18세 미만", "미성년", "학생", "청소년 판매", "미성년자 판매"],
            description="미성년자에게 주류 판매 금지 등 청소년 보호 규정"
        ),
        "식품위생법": LawInfo(
            name="식품위생법",
            law_id="식품위생법",
            keywords=["식품", "위생", "유해물질", "금지 재료", "첨가물", "표시", "광고", "허위", "과대광고"],
            description="식품의 위생적 관리와 안전성 확보, 표시광고 규정"
        ),
        "전통주등의산업진흥에관한법률": LawInfo(
            name="전통주등의산업진흥에관한법률",
            law_id="전통주등의산업진흥에관한법률",
            keywords=["전통주", "지역특산주", "요건", "인증", "제조", "양조", "누룩", "쌀"],
            description="전통주 산업 진흥 및 지역특산주 요건 규정"
        ),
        "표시광고법": LawInfo(
            name="표시광고의공정화에관한법률",
            law_id="표시광고의공정화에관한법률",
            keywords=["표시", "광고", "허위", "과대", "기만", "오인", "소비자"],
            description="상품의 표시광고 공정화 규정"
        ),
        "주세법": LawInfo(
            name="주세법",
            law_id="주세법",
            keywords=["주세", "주류", "제조", "면허", "도수", "알코올", "양조", "발효"],
            description="주류 제조, 판매에 관한 세금 및 면허 규정"
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
            description="투자 관련 규제 및 소비자 보호 규정"
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
            "keywords": ["숙취 없는", "숙취 해소", "숙취가 없는", "숙취가", "숙취없는", "숙취해소", "건강에 좋은", "치료", "약효", "효능", "100% 안전", "부작용 없는", "숙콤 없는", "숙취방지", "숙취예방", "해독", "간 보호", "간 건강", "약", "의약", "치료제", "완치", "완벽한", "무조건", "반드시", "확실한"],
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

        # API 엔드포인트
        self.law_api_url = "https://www.law.go.kr/DRF/lawSearch.do"
        self.law_detail_url = "https://www.law.go.kr/DRF/lawDetailService.do"

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

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.law_api_url, params=params)
                response.raise_for_status()

                data = response.json()

                # 조문 추출
                articles = []
                if "Law" in data:
                    for law in data["Law"]:
                        # 상세 정보 조회
                        detail_params = {
                            "OC": self.law_api_key,
                            "target": "law",
                            "type": "JSON",
                            "LAW_ID": law.get("법령ID", "")
                        }

                        try:
                            detail_response = await client.get(self.law_detail_url, params=detail_params)
                            detail_response.raise_for_status()
                            detail_data = detail_response.json()

                            # 조문 추출
                            if "법조문" in detail_data:
                                for article in detail_data["법조문"]:
                                    articles.append(Article(
                                        article_id=article.get("조문번호", ""),
                                        article_name=article.get("조문명칭", ""),
                                        content=article.get("조문내용", ""),
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

    async def _analyze_with_gemini(
        self,
        title: str,
        description: str,
        ingredients: str,
        articles: List[Article],
        content_type: ContentType
    ) -> List[ViolationDetail]:
        """
        Gemini API로 콘텐츠 분석

        Args:
            title: 제목
            description: 설명
            ingredients: 재료
            articles: 관련 조문
            content_type: 콘텐츠 타입

        Returns:
            위반 상세 정보 리스트
        """
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY가 설정되지 않음")
            return []

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            # 조문 정보를 텍스트로 변환
            articles_text = "\n".join([
                f"- {article.law_name} {article.article_name}: {article.content[:200]}..."
                for article in articles[:5]
            ])

            # 프롬프트 구성 (강화된 버전)
            prompt = f"""
당신은 전통주 관련 법률 전문가입니다. 다음 콘텐츠를 분석하여 법적 위반 여부를 판단해주세요.

**중요한 판단 원칙:**
1. 애매한 경우에는 보수적으로 violation: true로 판단하세요
2. 위반이 명백히 아닌 경우에만 false를 반환하세요
3. 판단 근거를 관련 법령 조문 번호와 함께 반드시 명시하세요
4. 과대광고/허위표시는 "숙취 없는", "건강에 좋은", "치료 효과" 등의 표현이 있으면 무조건 위반으로 간주하세요
5. 미성년자 타겟은 "청소년", "미성년자", "학생" 등의 표현이 있으면 무조건 위반으로 간주하세요

**분석 대상 콘텐츠:**
제목: {title}
설명: {description}
재료: {ingredients}
콘텐츠 타입: {content_type.value}

**관련 법령 조문:**
{articles_text}

**Few-shot 예시:**

예시 1:
제목: "숙취 없는 건강 막걸리"
설명: "숙취가 전혀 없고 건강에 좋은 막걸리"
재료: "쌀, 누룩, 물"
결과: {{"violation": true, "category": "과대광고/허위표시", "law": "식품위생법", "reason": "숙취 없다는 표현은 과대광고입니다", "article": "식품위생법 제4조"}}

예시 2:
제목: "미성년자용 딸기 막걸리"
설명: "학생들이 즐길 수 있는 맛있는 막걸리"
재료: "쌀, 딸기, 누룩, 물"
결과: {{"violation": true, "category": "미성년자 타겟", "law": "청소년보호법", "reason": "미성년자용 표현은 청소년보호법 위반입니다", "article": "청소년보호법 제6조"}}

예시 3:
제목: "경기도 쌀 막걸리, 전통 방식으로 제조"
설명: "경기도산 쌀 100% 사용, 전통 누룩으로 양조"
재료: "쌀, 누룩, 물"
결론: {{"violation": false, "category": "", "law": "", "reason": "법적 문제가 없습니다", "article": ""}}

**판단 기준:**
- 위반이 명백히 아닌 경우에만 false를 반환하세요
- 애매한 경우에는 반드시 true로 판단하세요
- 판단 근거를 조문과 함께 반드시 명시하세요

**이제 위 콘텐츠를 분석해주세요:**

답변 형식 (JSON만 반환, 다른 텍스트 없음):
{{
  "violation": true 또는 false,
  "violations": [
    {{
      "category": "위반 카테고리",
      "law": "관련 법령",
      "reason": "위반 이유 (구체적 근거 포함)",
      "article": "관련 조문 번호"
    }}
  ],
  "recommendation": "수정 권장사항"
}}
"""

            response = model.generate_content(prompt)
            result_text = response.text

            # JSON 파싱
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', result_text)
                if json_match:
                    result_text = json_match.group(0)

                result = json.loads(result_text)

                # violation 필드 확인
                violation = result.get("violation", False)

                violations = []
                if violation:
                    for v in result.get("violations", []):
                        violations.append(ViolationDetail(
                            category=v.get("category", ""),
                            law=v.get("law", ""),
                            reason=v.get("reason", ""),
                            article=v.get("article")
                        ))

                return violations

            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                logger.error(f"원본 응답: {result_text}")
                # 파싱 실패 시 보수적으로 true 반환
                return [ViolationDetail(
                    category="파싱오류",
                    law="알 수 없음",
                    reason="분석 실패로 보수적으로 차단합니다",
                    article=""
                )]

        except Exception as e:
            logger.error(f"Gemini 분석 실패: {e}")
            # 분석 실패 시 보수적으로 true 반환
            return [ViolationDetail(
                category="분석오류",
                law="알 수 없음",
                reason="분석 실패로 보수적으로 차단합니다",
                article=""
            )]

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

        # 빠른 키워드 감지 (Gemini 호출 전에 먼저 실행)
        text = (title + " " + description).replace(" ", "")
        for law, keywords in self.QUICK_VIOLATION_KEYWORDS.items():
            for kw in keywords:
                if kw.replace(" ", "") in text:
                    logger.info(f"위반 키워드 감지: {kw} ({law})")
                    return FilterResult(
                        violation=True,
                        details=[ViolationDetail(
                            category="키워드감지",
                            law=law,
                            reason=f"위반 키워드 감지: {kw}"
                        )],
                        recommendation=f"'{kw}' 표현을 수정해주세요"
                    )

        # 전체 텍스트 결합
        full_text = f"{title} {description} {ingredients}"

        # 위반 검사
        violations = []

        # MVP 1차 (필수)
        mvp1_categories = [
            ViolationCategory.MINOR_TARGET,
            ViolationCategory.ILLEGAL_INGREDIENTS,
            ViolationCategory.REGIONAL_REQUIREMENTS,
            ViolationCategory.FALSE_ADVERTISING
        ]

        # MVP 2차 (펀딩인 경우 추가)
        if content_type == ContentType.FUNDING:
            mvp1_categories.extend([
                ViolationCategory.UNLICENSED_MANUFACTURING,
                ViolationCategory.UNREALISTIC_ABV,
                ViolationCategory.TRADEMARK_INFRINGEMENT,
                ViolationCategory.FUNDING_REGULATION
            ])

        # 키워드 기반 검사
        for category in mvp1_categories:
            if self._check_violation_keywords(full_text, category):
                laws = self.VIOLATION_KEYWORDS[category]["laws"]

                for law_name in laws:
                    # 관련 조문 조회
                    law_info = self.LAWS.get(law_name)
                    if law_info:
                        articles = await self.get_relevant_articles(law_name, law_info.keywords)

                        # Gemini 분석
                        gemini_violations = await self._analyze_with_gemini(
                            title, description, ingredients, articles, content_type
                        )

                        violations.extend(gemini_violations)

        # 결과 생성
        if violations:
            recommendation = "다음 문제를 수정해주세요: " + ", ".join([v.reason for v in violations])
        else:
            recommendation = "법적 문제가 없습니다."

        result = FilterResult(
            violation=len(violations) > 0,
            details=violations,
            recommendation=recommendation
        )

        logger.info(f"필터링 완료: 위반={result.violation}, 위반 수={len(violations)}")

        return result

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
