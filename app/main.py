"""
주담 AI 서버 - FastAPI 진입점
"""

import logging
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 기존 모듈 임포트
from app.core.recommender import AdvancedMakgeolliRecommender
from app.core.survey_converter import SurveyToVectorConverter, SurveyResponse
from app.law_client import LawClient, ContentType, FilterResult
from app.insight import InsightDashboard, InsightRequest, InsightResponse
from app.rag import TraditionalAlcoholRAG, RAGSearchRequest, RAGSearchResponse
from app.recipe import RecipeAI
from app.image_generator import ImageGenerator
from app.chat import router as chat_router
from app.models import (
    TasteVector, RecommendRequest, RecommendResponse,
    TasteUpdateRequest, TasteUpdateResponse,
    TasteHistorySummaryResponse,
    FoodRecommendRequest, FoodRecommendResponse,
    HealthResponse,
    LawFilterRequest,
    SurveyConvertResponse,
    SubIngredientsRequest, SubIngredientsResponse,
    FlavorTagsRequest, FlavorTagsResponse,
    SummaryRequest, SummaryResponse,
    FundingRegisterRequest, FundingRegisterResponse,
    FundingGetResponse,
    FundingTasteUpdateRequest, FundingTasteUpdateResponse,
    RecipeValidateRequest, RecipeValidateResponse,
    RecipeRegisterRequest, RecipeRegisterResponse,
)
from app.db import db

TASTE_AXES = {'sweetness', 'body', 'carbonation', 'flavor', 'alcohol', 'acidity', 'aroma_intensity', 'finish'}

# Gemini API 가용성 플래그 (한도 초과 시 False로 설정)
GEMINI_AVAILABLE = True

# 서버 시작 시간
_server_start_time = datetime.now()

# 인메모리 사용자 프로필 저장소
_user_profiles: Dict[str, Dict] = {}

# 인메모리 응답 캐시
_cache: Dict[str, Dict] = {}


def get_cache(key: str):
    entry = _cache.get(key)
    if entry and datetime.now() < entry['expires']:
        return entry['value']
    return None


def set_cache(key: str, value, ttl_minutes: int = 60):
    _cache[key] = {
        'value': value,
        'expires': datetime.now() + timedelta(minutes=ttl_minutes),
    }

# 추천 시스템 초기화
_recommender = AdvancedMakgeolliRecommender()
_survey_converter = SurveyToVectorConverter()
_law_client = LawClient()
_insight_dashboard = InsightDashboard()
_rag_system = TraditionalAlcoholRAG()
_recipe_ai = RecipeAI()
_image_generator = ImageGenerator()

# FastAPI 인스턴스 생성
app = FastAPI(
    title="주담 AI 서버",
    description="술BTI 추천 · 법률 필터링 · AI 인사이트 대시보드 · RAG",
    version="0.3.0"
)

# 추천 시스템을 app에 연결
app.state.recommender = _recommender
app.state.survey_converter = _survey_converter
app.state.law_client = _law_client
app.state.insight_dashboard = _insight_dashboard
app.state.rag_system = _rag_system
app.state.recipe_ai = _recipe_ai

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"status": "error", "message": "요청한 경로를 찾을 수 없습니다."})


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"status": "error", "message": "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."})


app.include_router(chat_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    # DB 연결
    try:
        await db.connect()
        await db.initialize_tables()
        _recommender.set_db(db)

        # DB에서 데이터 로드 시도
        loaded_from_db = await _recommender.load_data_from_db()

        # DB가 비어있으면 JSON 파일에서 초기화
        if not loaded_from_db:
            await _recommender.initialize_db_from_json()

        # DB에서 취향 히스토리 로드
        await _recommender.load_taste_history_from_db()

        logger.info(f"서버 시작 완료 - 데이터: {len(_recommender.drinks)}개, DB 연결: {_recommender.db_connected}")
    except Exception as e:
        logger.warning(f"DB 연결 실패 (JSON fallback 사용): {e}")
        _recommender.db_connected = False

    app.state.user_profiles = _user_profiles

    # 캐시 워밍업 (백그라운드)
    async def warm_cache():
        try:
            warm_targets = [
                {'main_ingredient': '이천 쌀', 'region': '경기도 이천'},
                {'main_ingredient': '제주 감귤', 'region': '제주도'},
                {'main_ingredient': '안동 쌀', 'region': '경상북도 안동'},
                {'main_ingredient': '전주 쌀', 'region': '전라북도 전주'},
            ]
            for target in warm_targets:
                cache_key = f"recipe_sub_{hash(target['main_ingredient']+target['region'])}"
                if not get_cache(cache_key):
                    try:
                        result = await _recipe_ai.suggest_sub_ingredients(
                            target['main_ingredient'], target['region']
                        )
                        set_cache(cache_key, result, ttl_minutes=1440)
                        logger.info(f"캐시 워밍업 완료: {target['region']}")
                    except Exception as e:
                        logger.warning(f"캐시 워밍업 실패: {target['region']} - {e}")
        except Exception as e:
            logger.warning(f"캐시 워밍업 전체 실패: {e}")

    import asyncio as _asyncio
    _asyncio.create_task(warm_cache())


# 헬퍼 함수
def clean_string(value) -> str:
    """NaN 또는 None을 빈 문자열로 변환"""
    if value is None or (isinstance(value, float) and str(value) == 'nan'):
        return ""
    return str(value) if value else ""


def raise_api_error(e: Exception, default_msg: str = "서비스 오류가 발생했습니다. 잠시 후 다시 시도해주세요.") -> None:
    """Gemini 에러 → 명확한 한글 HTTPException 변환"""
    s = str(e)
    is_quota = '429' in s or 'quota exceeded' in s.lower() or 'resource_exhausted' in s.lower()
    if is_quota or '현재 AI 서비스' in s or 'AI 서비스에 연결' in s:
        raise HTTPException(status_code=503, detail="현재 AI 서비스가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요.")
    raise HTTPException(status_code=500, detail=default_msg)


# 술BTI 16가지 유형 매핑
BTI_TYPE_MAPPING = {
    "SHFC": {
        "name": "꿀단지에 빠진 인절미",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["꿀 막걸리", "밤 막걸리", "탄산 생막걸리"]
    },
    "SHFU": {
        "name": "탄산 톡톡 딸기 요거트",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["딸기 탄산막걸리", "복숭아 생막걸리", "유자 탁주"]
    },
    "SHMC": {
        "name": "쫀득쫀득 꿀 찹쌀떡",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["찹쌀탁주", "원주 막걸리", "고구마 막걸리"]
    },
    "SHMU": {
        "name": "포근포근 꽃복숭아",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["망고 막걸리", "블루베리 탁주", "샤인머스캣 막걸리"]
    },
    "SLFC": {
        "name": "청량함 가득 사과 푸딩",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["저도수 생막걸리", "쌀 막걸리", "캔 막걸리"]
    },
    "SLFU": {
        "name": "팝핑 과일 에이드",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["자몽 막걸리", "레몬 탁주", "오미자 탄산막걸리"]
    },
    "SLMC": {
        "name": "햇살 머금은 식혜",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["맑은 탁주", "단술", "저도수 쌀막걸리"]
    },
    "SLMU": {
        "name": "산들바람 머금은 화전",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["꽃잎 막걸리", "허브 탁주", "사과 막걸리"]
    },
    "DHFC": {
        "name": "바삭하게 터지는 현미 누룽지",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["고도수 생막걸리", "드라이한 탁주", "호밀 막걸리"]
    },
    "DHFU": {
        "name": "반전매력 고추냉이",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["오미자 탄산막걸리", "생강 탁주", "쑥 막걸리"]
    },
    "DHMC": {
        "name": "묵묵한 바위 속 숭늉",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["무감미료 탁주", "고도수 원주", "옥수수 막걸리"]
    },
    "DHMU": {
        "name": "안개 낀 숲속의 황금사과",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["산미 특화 막걸리", "약재 향 탁주", "드라이 과일막걸리"]
    },
    "DLFC": {
        "name": "청량한 대나무 숲의 차",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["가벼운 드라이 막걸리", "탄산 약주", "쌀 생막걸리"]
    },
    "DLFU": {
        "name": "차가운 도시의 샹그리아",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["드라이 유자막걸리", "진저 탁주", "탄산 베리막걸리"]
    },
    "DLMC": {
        "name": "대숲에 앉은 맑은 백설기",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["정통 드라이 탁주", "맑은 막걸리", "가벼운 누룩주"]
    },
    "DLMU": {
        "name": "빗소리 들리는 다실의 꽃차",
        "tags": ["#부드러운단맛", "#화사한과일향"],
        "drinks": ["산미 있는 가벼운 탁주", "허브 드라이막걸리", "차 콜라보 막걸리"]
    }
}


def determine_bti_code(sweetness: float, body: float, carbonation: float, flavor: float, alcohol: float = 5.0) -> str:
    """
    맛 벡터에서 술BTI 코드 판정

    Args:
        sweetness: 단맛 (0~10)
        body: 바디감 (0~10)
        carbonation: 탄산 (0~10)
        flavor: 풍미 (0~10)
        alcohol: 도수 (0~10)

    Returns:
        5자리 술BTI 코드 (예: SHMCH)
    """
    s_d = 'S' if sweetness >= 5 else 'D'
    h_l = 'H' if body >= 5 else 'L'
    f_m = 'F' if carbonation >= 5 else 'M'
    c_u = 'U' if flavor >= 5 else 'C'
    a   = 'H' if alcohol >= 9 else 'L'
    return f"{s_d}{h_l}{f_m}{c_u}{a}"


# 엔드포인트
@app.get("/")
def root():
    """루트 엔드포인트"""
    return {
        "message": "주담 AI 서버 정상 동작",
        "version": "0.3.0",
        "endpoints": {
            "recommend": "/api/recommend",
            "taste_update": "/api/taste/update",
            "taste_history": "/api/taste/history/{user_id}",
            "food_recommend": "/api/food/recommend",
            "survey_convert": "/api/survey/convert",
            "taste_profile": "/api/taste/profile/{user_id}",
            "recipe_suggest_sub_ingredients": "/api/recipe/suggest-sub-ingredients",
            "recipe_suggest_flavor_tags": "/api/recipe/suggest-flavor-tags",
            "recipe_suggest_summary": "/api/recipe/suggest-summary",
            "law_filter": "/api/law/filter",
            "law_info": "/api/law/info",
            "insight": "/api/insight",
            "rag_search": "/api/rag/search",
            "chat": "/api/chat",
            "health": "/health"
        }
    }


@app.get("/health")
def health():
    """헬스체크 엔드포인트 (기능별 상태 포함)"""
    try:
        recommender = app.state.recommender
        api_key    = os.getenv("GEMINI_API_KEY")
        law_key    = os.getenv("LAW_API_KEY")

        # 기능별 상태 판정 (GEMINI_AVAILABLE=False면 "limited")
        recommend_ok = "ok" if len(recommender.drinks) > 0 else "no_data"
        if not api_key:
            recipe_ok = law_ok = chat_ok = "no_gemini_key"
        elif not GEMINI_AVAILABLE:
            recipe_ok = law_ok = chat_ok = "limited"
        else:
            recipe_ok = law_ok = chat_ok = "ok"
        insight_ok = "ok" if len(recommender.drinks) > 0 else "no_data"

        uptime = int((datetime.now() - _server_start_time).total_seconds())

        return {
            "status": "ok",
            "version": "0.3.0",
            "data_count": len(recommender.drinks),
            "funding_count": len(_fundings),
            "recipe_count": len(_recipes),
            "user_count": len(_user_profiles),
            "gemini_key_loaded": bool(api_key),
            "gemini_available": GEMINI_AVAILABLE,
            "law_key_loaded": bool(law_key),
            "db_connected": recommender.db_connected,
            "uptime_seconds": uptime,
            "api_status": {
                "recommend": recommend_ok,
                "recipe":    recipe_ok,
                "law":       law_ok,
                "chat":      chat_ok,
                "insight":   insight_ok
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.post("/api/recommend", response_model=List[RecommendResponse])
async def recommend(request: RecommendRequest):
    """
    맛 벡터 기반 추천

    Args:
        request: 추천 요청 (user_vector 또는 user_id 중 하나 필수)

    Returns:
        추천 결과 리스트
    """
    if request.user_vector is None and not request.user_id:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "user_vector 또는 user_id 중 하나는 필수입니다."})
    if not (1 <= request.top_k <= 50):
        raise HTTPException(status_code=400, detail={"status": "error", "message": "top_k는 1~50 사이여야 합니다."})

    try:
        recommender = app.state.recommender

        # 맛 벡터 결정: user_vector 우선, user_id로 메모리→DB 순서로 조회
        if request.user_vector is not None:
            user_vector = request.user_vector.model_dump()
        elif request.user_id:
            mem = _user_profiles.get(request.user_id)
            if mem:
                user_vector = mem['taste_vector']
            else:
                db_profile = await db.get_user_profile(request.user_id)
                if db_profile and db_profile.get('taste_vector'):
                    import json as _json
                    tv = db_profile['taste_vector']
                    user_vector = _json.loads(tv) if isinstance(tv, str) else tv
                    _user_profiles[request.user_id] = {'taste_vector': user_vector}
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="user_vector 또는 저장된 user_id 중 하나를 제공해주세요."
                    )
        else:
            raise HTTPException(
                status_code=400,
                detail="user_vector 또는 저장된 user_id 중 하나를 제공해주세요."
            )

        # 추천
        recommendations = recommender.recommend(
            user_vector=user_vector,
            top_k=request.top_k,
            exclude_ids=request.exclude_ids
        )

        # 응답 변환
        response = []
        for rec in recommendations:
            response.append(RecommendResponse(
                id=rec['id'],
                name=rec['name'],
                similarity=rec['similarity'],
                similarity_percent=rec.get('similarity_percent', round(rec['similarity'] * 100, 1)),
                abv=rec['abv'],
                brewery=clean_string(rec.get('brewery')),
                region=clean_string(rec.get('region')),
                features=clean_string(rec.get('features')),
                taste_vector=TasteVector(**rec['taste_vector']),
                match_reason=rec.get('match_reason', []),
                is_funding=rec.get('is_funding', False),
                status=rec.get('status', 'available'),
            ))

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/taste/update")
async def taste_update(request: TasteUpdateRequest):
    """
    사용자 취향 업데이트

    Args:
        request: 취향 업데이트 요청

    Returns:
        업데이트 결과
    """
    if request.rating is None and not request.ratings:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "rating(별점) 또는 ratings(축별 수치) 중 하나는 필수입니다."})

    try:
        recommender = app.state.recommender

        await recommender.update_user_taste(
            user_id=request.user_id,
            drink_id=request.drink_id,
            rating=request.rating,
            tags=request.tags,
            ratings=request.ratings
        )

        return {
            "status": "success",
            "message": f"사용자 {request.user_id}의 취향이 업데이트되었습니다."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/taste/history/{user_id}")
def taste_history(user_id: str):
    """
    사용자 취향 히스토리 조회

    Args:
        user_id: 사용자 ID

    Returns:
        취향 히스토리
    """
    try:
        recommender = app.state.recommender

        history = recommender.user_taste_history.get(user_id, [])

        # 진화된 맛 벡터 계산
        evolved_vector = recommender.get_evolved_taste_vector(user_id)

        return {
            "user_id": user_id,
            "history_count": len(history),
            "history": history,
            "evolved_taste_vector": evolved_vector
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/food/recommend", response_model=List[FoodRecommendResponse])
def food_recommend(request: FoodRecommendRequest):
    """
    음식 기반 추천

    Args:
        request: 음식 기반 추천 요청

    Returns:
        추천 결과 리스트
    """
    if not request.food.strip():
        raise HTTPException(status_code=400, detail={"status": "error", "message": "음식 이름을 입력해주세요."})

    try:
        cache_key = f"food:{request.food}:{request.top_k}"
        cached = get_cache(cache_key)
        if cached is not None:
            logger.info(f"음식 캐시 히트: {cache_key}")
            return cached

        recommender = app.state.recommender

        # 추천
        recommendations = recommender.recommend_by_food(
            food=request.food,
            top_k=request.top_k
        )

        # 응답 변환
        response = []
        for rec in recommendations:
            response.append(FoodRecommendResponse(
                id=rec['id'],
                name=rec['name'],
                abv=rec['abv'],
                brewery=clean_string(rec.get('brewery')),
                region=clean_string(rec.get('region')),
                features=clean_string(rec.get('features')),
                taste_vector=TasteVector(**rec['taste_vector']),
                reason=rec['reason']
            ))

        set_cache(cache_key, response, ttl_minutes=1440)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/survey/convert", response_model=SurveyConvertResponse)
async def survey_convert(survey: SurveyResponse, user_id: Optional[str] = None):
    """
    술BTI 설문 → 맛 벡터 변환

    Args:
        survey: 설문 응답
        user_id: 저장할 사용자 ID (선택)

    Returns:
        맛 벡터 + BTI 유형 정보
    """
    try:
        survey_converter = app.state.survey_converter
        full = survey_converter.convert(survey)
        taste_vector = {k: v for k, v in full.items() if k in TASTE_AXES}

        full.pop('food_pairing', None)

        response = SurveyConvertResponse(
            status="success",
            taste_vector=taste_vector,
            bti_code=full.get('bti_code', ''),
            character_name=full.get('character_name', ''),
            alcohol_label=full.get('alcohol_label', ''),
            experience_level=full.get('experience_level', ''),
            preferred_abv=full.get('preferred_abv', ''),
            preferred_body=full.get('preferred_body', ''),
            preferred_fruit=full.get('preferred_fruit', ''),
            preferred_food_pairing=full.get('preferred_food_pairing', []),
            preferred_aroma=full.get('preferred_aroma', []),
            taste_profile_summary=full.get('taste_profile_summary', ''),
        )

        if user_id:
            profile_data = response.model_dump()
            _user_profiles[user_id] = profile_data
            logger.info(f"사용자 프로필 메모리 저장: {user_id}")
            try:
                await db.upsert_user_profile(user_id, profile_data)
                logger.info(f"사용자 프로필 DB 저장: {user_id}")
            except Exception as db_err:
                logger.warning(f"DB 저장 실패 (메모리만 유지): {db_err}")

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/taste/profile/{user_id}")
async def get_taste_profile(user_id: str):
    """
    저장된 사용자 취향 프로필 조회 (메모리 → DB 순)

    Args:
        user_id: 사용자 ID

    Returns:
        survey/convert 결과 전체
    """
    # 메모리 우선
    if user_id in _user_profiles:
        return _user_profiles[user_id]

    # DB fallback
    try:
        db_profile = await db.get_user_profile(user_id)
        if db_profile:
            import json as _json
            for field in ('taste_vector', 'preferred_food_pairing', 'preferred_aroma'):
                v = db_profile.get(field)
                if isinstance(v, str):
                    db_profile[field] = _json.loads(v)
            _user_profiles[user_id] = db_profile
            return db_profile
    except Exception as e:
        logger.warning(f"DB 프로필 조회 실패: {e}")

    raise HTTPException(
        status_code=404,
        detail=f"사용자 '{user_id}'의 프로필이 없습니다. survey/convert를 먼저 호출해주세요."
    )




@app.post("/api/recipe/suggest-sub-ingredients", response_model=SubIngredientsResponse)
async def suggest_sub_ingredients(request: SubIngredientsRequest):
    """
    서브재료 추천

    Args:
        request: 서브재료 추천 요청

    Returns:
        서브재료 리스트
    """
    if not GEMINI_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI 서비스 점검 중입니다. 잠시 후 다시 시도해주세요.")
    try:
        cache_key = f"recipe_sub_{hash(request.main_ingredient + request.region)}"
        cached = get_cache(cache_key)
        if cached is not None:
            logger.info(f"서브재료 캐시 히트: {request.main_ingredient}/{request.region}")
            return cached

        recipe_ai = app.state.recipe_ai

        result = await recipe_ai.suggest_sub_ingredients(
            main_ingredient=request.main_ingredient,
            region=request.region
        )

        response_obj = SubIngredientsResponse(sub_ingredients=result["sub_ingredients"])
        set_cache(cache_key, response_obj, ttl_minutes=1440)
        return response_obj

    except Exception as e:
        raise_api_error(e, "서브재료 추천 중 오류가 발생했습니다.")


@app.post("/api/recipe/suggest-flavor-tags", response_model=FlavorTagsResponse)
async def suggest_flavor_tags(request: FlavorTagsRequest):
    """
    맛 태그 추천

    Args:
        request: 맛 태그 추천 요청

    Returns:
        맛 태그 리스트
    """
    if not GEMINI_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI 서비스 점검 중입니다. 잠시 후 다시 시도해주세요.")
    try:
        recipe_ai = app.state.recipe_ai

        result = await recipe_ai.suggest_flavor_tags(
            title=request.title,
            main_ingredient=request.main_ingredient,
            sub_ingredients=request.sub_ingredients,
            abv_range=request.abv_range
        )

        return FlavorTagsResponse(flavor_tags=result["flavor_tags"])

    except Exception as e:
        raise_api_error(e, "맛 태그 추천 중 오류가 발생했습니다.")


@app.post("/api/recipe/suggest-summary", response_model=SummaryResponse)
async def suggest_summary(request: SummaryRequest):
    """
    요약문 생성

    Args:
        request: 요약문 생성 요청

    Returns:
        요약문
    """
    if not GEMINI_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI 서비스 점검 중입니다. 잠시 후 다시 시도해주세요.")
    try:
        recipe_ai = app.state.recipe_ai

        result = await recipe_ai.suggest_summary(
            title=request.title,
            main_ingredient=request.main_ingredient,
            sub_ingredients=request.sub_ingredients,
            abv_range=request.abv_range,
            flavor_tags=request.flavor_tags,
            concept=request.concept
        )

        return SummaryResponse(summary=result["summary"])

    except Exception as e:
        raise_api_error(e, "요약문 생성 중 오류가 발생했습니다.")


@app.post("/api/law/filter")
async def law_filter(request: LawFilterRequest):
    """
    콘텐츠 법률 필터링

    Args:
        request: 필터링 요청

    Returns:
        필터링 결과
    """
    if not GEMINI_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI 서비스 점검 중입니다. 잠시 후 다시 시도해주세요.")
    try:
        cache_key = f"law:{request.content_type}:{request.title}:{request.description}"
        cached = get_cache(cache_key)
        if cached is not None:
            logger.info(f"법률 캐시 히트: {cache_key[:60]}")
            return cached

        law_client = app.state.law_client

        # 콘텐츠 타입 변환
        ct = ContentType.RECIPE if request.content_type == "recipe" else ContentType.FUNDING

        result = await law_client.filter_content(
            title=request.title,
            description=request.description,
            ingredients=request.ingredients,
            content_type=ct
        )

        response_data = {
            "violation": result.violation,
            "details": [
                {
                    "category": d.category,
                    "law": d.law,
                    "reason": d.reason,
                    "article": d.article
                }
                for d in result.details
            ],
            "recommendation": result.recommendation
        }
        set_cache(cache_key, response_data, ttl_minutes=60)
        return response_data

    except Exception as e:
        raise_api_error(e, "법률 필터링 중 오류가 발생했습니다.")


@app.get("/api/law/info")
def get_law_info():
    """
    법령 정보 조회

    Returns:
        법령 정보 리스트
    """
    try:
        law_client = app.state.law_client

        laws = law_client.get_all_laws()

        return {
            "status": "success",
            "laws": [
                {
                    "name": law.name,
                    "law_id": law.law_id,
                    "keywords": law.keywords,
                    "description": law.description
                }
                for law in laws
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/insight")
async def get_insights(period: str = "week"):
    """
    인사이트 대시보드

    Args:
        period: 기간 (day, week, month)

    Returns:
        인사이트 결과 (ai_report 포함)
    """
    try:
        insight_dashboard = app.state.insight_dashboard

        insights = await insight_dashboard.get_insights(period=period)

        return insights

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/search")
def rag_search(request: RAGSearchRequest):
    """
    RAG 문서 검색

    Args:
        request: RAG 검색 요청

    Returns:
        검색 결과
    """
    try:
        cache_key = f"rag:{request.query}:{request.top_k}:{request.category}"
        cached = get_cache(cache_key)
        if cached is not None:
            logger.info(f"RAG 캐시 히트: {cache_key[:60]}")
            return cached

        rag_system = app.state.rag_system

        results = rag_system.search(
            query=request.query,
            top_k=request.top_k,
            category=request.category
        )

        set_cache(cache_key, results, ttl_minutes=60)
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# =====================================================
# 3단계: 크롤러 모니터 API
# =====================================================

@app.post("/api/crawler/check")
def crawler_check():
    """
    koreansool.co.kr 에서 새로운 전통주를 감지하고 auto_pipeline 을 트리거합니다.

    Returns:
        감지 결과 (new_count, new_items, total_seen)
    """
    try:
        from app.crawler.traditional_alcohol_monitor import check_new_entries
        from app.auto_pipeline import AutoPipeline

        auto_pipeline = AutoPipeline()
        result = check_new_entries(auto_pipeline=auto_pipeline)
        return result

    except Exception as e:
        logger.error(f"크롤러 체크 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 4단계: 전통주 등록 요청 API (메모리 기반)
# =====================================================

# 메모리 기반 등록 요청 저장소
_drink_requests: List[Dict] = []
_drink_request_id_counter = [0]


class ImageGenerateRequest(BaseModel):
    name: str
    description: str
    flavor_tags: List[str] = []
    region: Optional[str] = None


class DrinkRequestCreate(BaseModel):
    user_id: str = Field(..., description="요청자 사용자 ID")
    name: str = Field(..., description="전통주 이름")
    brewery: Optional[str] = Field(None, description="양조장")
    region: Optional[str] = Field(None, description="지역")
    description: Optional[str] = Field(None, description="설명")


@app.post("/api/drinks/request")
def create_drink_request(request: DrinkRequestCreate):
    """
    사용자 전통주 등록 요청 접수

    Args:
        request: 등록 요청 정보

    Returns:
        접수 결과 및 요청 ID
    """
    _drink_request_id_counter[0] += 1
    req_id = _drink_request_id_counter[0]

    record = {
        "id": req_id,
        "user_id": request.user_id,
        "name": request.name,
        "brewery": request.brewery or "",
        "region": request.region or "",
        "description": request.description or "",
        "status": "pending",
        "requested_at": datetime.now().isoformat(),
        "approved_at": None,
        "taste_vector": None,
    }
    _drink_requests.append(record)

    logger.info(f"전통주 등록 요청 접수: #{req_id} {request.name} (by {request.user_id})")

    return {"status": "success", "message": "등록 요청이 접수되었습니다.", "request_id": req_id}


@app.get("/api/drinks/requests")
def list_drink_requests(status: Optional[str] = None):
    """
    전통주 등록 요청 목록 조회 (관리자용)

    Args:
        status: 필터 (pending / approved / all)

    Returns:
        등록 요청 목록
    """
    if status and status != "all":
        filtered = [r for r in _drink_requests if r["status"] == status]
    else:
        filtered = list(_drink_requests)

    return {"status": "success", "total": len(filtered), "requests": filtered}


@app.post("/api/drinks/requests/{request_id}/approve")
def approve_drink_request(request_id: int):
    """
    전통주 등록 요청 승인 + auto_pipeline 실행

    Args:
        request_id: 요청 ID

    Returns:
        승인 결과 (taste_vector 포함)
    """
    record = next((r for r in _drink_requests if r["id"] == request_id), None)
    if not record:
        raise HTTPException(status_code=404, detail=f"요청 ID {request_id} 를 찾을 수 없습니다.")

    if record["status"] == "approved":
        return {"status": "already_approved", "message": "이미 승인된 요청입니다.", "request": record}

    try:
        from app.auto_pipeline import AutoPipeline

        pipeline = AutoPipeline()
        drink_data = {
            "name": record["name"],
            "brewery": record["brewery"],
            "region": record["region"],
            "description": record["description"],
            "features": record["description"],
            "ingredients": "",
            "abv": 0.0,
        }
        vector = pipeline.create_taste_vector(drink_data, use_gemini=True)

        record["status"] = "approved"
        record["approved_at"] = datetime.now().isoformat()
        record["taste_vector"] = vector

        logger.info(f"전통주 등록 요청 승인 완료: #{request_id} {record['name']}")

        return {"status": "success", "message": "승인 완료. 맛 벡터가 생성되었습니다.", "request": record}

    except Exception as e:
        logger.error(f"승인 처리 중 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 펀딩 맛지표 API
# =====================================================

# 인메모리 펀딩 저장소: funding_id → 등록 데이터
_fundings: Dict[str, Dict] = {}


@app.post("/api/funding/register", response_model=FundingRegisterResponse)
async def funding_register(request: FundingRegisterRequest):
    """
    펀딩 전통주 등록: 맛지표 입력 → 맛벡터 생성 → 추천 풀 편입

    Args:
        request: 펀딩 등록 요청

    Returns:
        등록 결과 + 생성된 맛벡터
    """
    if request.funding_id in _fundings:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "이미 등록된 펀딩 ID입니다."})
    if request.abv is not None and (request.abv <= 0 or request.abv > 100):
        raise HTTPException(status_code=400, detail={"status": "error", "message": "도수는 0~100 사이여야 합니다."})

    try:
        recommender = app.state.recommender

        if request.taste_input is not None:
            # 직접 입력된 맛지표 사용
            taste_vector = request.taste_input.model_dump()
            source = "direct_input"
        else:
            # Gemini auto_pipeline으로 자동 생성
            from app.auto_pipeline import AutoPipeline
            pipeline = AutoPipeline()
            drink_data = {
                "name": request.name,
                "brewery": request.brewery or "",
                "region": request.region or "",
                "description": request.description or "",
                "features": request.description or "",
                "ingredients": request.main_ingredient or "",
                "abv": request.abv or 0.0,
            }
            taste_vector = pipeline.create_taste_vector(drink_data, use_gemini=True)
            source = "gemini_auto"

        # 추천 풀 편입
        drink_entry = {
            "id": request.funding_id,
            "name": request.name,
            "abv": request.abv or 0.0,
            "brewery": request.brewery or "",
            "region": request.region or "",
            "features": request.description or "",
            "description": request.description or "",
            "ingredients": request.main_ingredient or "",
            "taste_vector": taste_vector,
            "is_funding": True,
        }
        existing_ids = {d["id"] for d in recommender.drinks}
        if request.funding_id not in existing_ids:
            recommender.drinks.append(drink_entry)
        else:
            for i, d in enumerate(recommender.drinks):
                if d["id"] == request.funding_id:
                    recommender.drinks[i] = drink_entry
                    break

        # DB 저장 시도
        if recommender.db_connected:
            try:
                await db.upsert_drink(drink_entry)
            except Exception as db_err:
                logger.warning(f"펀딩 DB 저장 실패 (메모리만 유지): {db_err}")

        # 인메모리 저장
        _fundings[request.funding_id] = {
            **drink_entry,
            "main_ingredient": request.main_ingredient or "",
            "brewery_user_id": request.brewery_user_id or "",
            "source": source,
            "registered_at": datetime.now().isoformat(),
        }

        logger.info(f"펀딩 등록 완료: {request.funding_id} ({request.name}) source={source}")

        return FundingRegisterResponse(
            status="success",
            funding_id=request.funding_id,
            name=request.name,
            taste_vector=TasteVector(**taste_vector),
            source=source,
            message="펀딩 전통주가 추천 풀에 편입되었습니다."
        )

    except Exception as e:
        logger.error(f"펀딩 등록 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/funding/{funding_id}", response_model=FundingGetResponse)
def funding_get(funding_id: str):
    """
    등록된 펀딩 정보 + 맛벡터 조회

    Args:
        funding_id: 펀딩 ID

    Returns:
        펀딩 정보 + 맛벡터
    """
    record = _fundings.get(funding_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"펀딩 '{funding_id}'를 찾을 수 없습니다.")

    return FundingGetResponse(
        funding_id=funding_id,
        name=record["name"],
        brewery=record.get("brewery"),
        region=record.get("region"),
        description=record.get("description"),
        abv=record.get("abv"),
        main_ingredient=record.get("main_ingredient"),
        brewery_user_id=record.get("brewery_user_id"),
        taste_vector=TasteVector(**record["taste_vector"]),
        registered_at=record.get("registered_at", "")
    )


@app.post("/api/funding/{funding_id}/taste-update", response_model=FundingTasteUpdateResponse)
async def funding_taste_update(funding_id: str, request: FundingTasteUpdateRequest):
    """
    샘플 시음 후 맛벡터 보정

    Args:
        funding_id: 펀딩 ID
        request: 보정된 맛지표 (8축)

    Returns:
        보정 결과
    """
    record = _fundings.get(funding_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"펀딩 '{funding_id}'를 찾을 수 없습니다.")

    updated_vector = request.taste_input.model_dump()

    # 인메모리 업데이트
    record["taste_vector"] = updated_vector
    _fundings[funding_id] = record

    # 추천 풀 업데이트
    recommender = app.state.recommender
    for d in recommender.drinks:
        if d["id"] == funding_id:
            d["taste_vector"] = updated_vector
            break

    # DB 업데이트 시도
    if recommender.db_connected:
        try:
            await db.upsert_drink({**record, "taste_vector": updated_vector})
        except Exception as db_err:
            logger.warning(f"펀딩 맛벡터 DB 업데이트 실패: {db_err}")

    logger.info(f"펀딩 맛벡터 보정 완료: {funding_id}")

    return FundingTasteUpdateResponse(
        status="success",
        funding_id=funding_id,
        taste_vector=TasteVector(**updated_vector),
        message="맛벡터가 보정되어 추천 풀에 반영되었습니다."
    )


# =====================================================
# 레시피 등록 → 추천 풀 연동 API
# =====================================================

# 인메모리 레시피 저장소: recipe_id → 등록 데이터
_recipes: Dict[str, Dict] = {}


@app.post("/api/recipe/register", response_model=RecipeRegisterResponse)
async def recipe_register(request: RecipeRegisterRequest):
    """
    레시피 등록: 맛지표 입력 → 맛벡터 생성 → 추천 풀 편입

    Args:
        request: 레시피 등록 요청

    Returns:
        등록 결과 + 생성된 맛벡터
    """
    try:
        recommender = app.state.recommender

        if request.taste_input is not None:
            taste_vector = request.taste_input.model_dump()
            source = "direct_input"
        elif GEMINI_AVAILABLE:
            from app.auto_pipeline import AutoPipeline
            pipeline = AutoPipeline()
            drink_data = {
                "name": request.title,
                "brewery": "",
                "region": "",
                "description": request.description or "",
                "features": ", ".join(request.flavor_tags),
                "ingredients": request.main_ingredient + (
                    ", " + ", ".join(request.sub_ingredients) if request.sub_ingredients else ""
                ),
                "abv": 0.0,
            }
            taste_vector = pipeline.create_taste_vector(drink_data, use_gemini=True)
            source = "gemini_auto"
        else:
            raise HTTPException(
                status_code=503,
                detail="AI 서비스 점검 중입니다. taste_input을 직접 입력해주세요."
            )

        drink_entry = {
            "id": request.recipe_id,
            "name": request.title,
            "abv": 0.0,
            "brewery": "",
            "region": "",
            "features": ", ".join(request.flavor_tags),
            "description": request.description or "",
            "ingredients": request.main_ingredient,
            "taste_vector": taste_vector,
        }
        existing_ids = {d["id"] for d in recommender.drinks}
        if request.recipe_id not in existing_ids:
            recommender.drinks.append(drink_entry)
        else:
            for i, d in enumerate(recommender.drinks):
                if d["id"] == request.recipe_id:
                    recommender.drinks[i] = drink_entry
                    break

        _recipes[request.recipe_id] = {
            **drink_entry,
            "user_id": request.user_id,
            "main_ingredient": request.main_ingredient,
            "sub_ingredients": request.sub_ingredients,
            "abv_range": request.abv_range,
            "flavor_tags": request.flavor_tags,
            "source": source,
            "registered_at": datetime.now().isoformat(),
        }

        logger.info(f"레시피 등록 완료: {request.recipe_id} ({request.title}) source={source}")

        return RecipeRegisterResponse(
            status="success",
            recipe_id=request.recipe_id,
            title=request.title,
            taste_vector=TasteVector(**taste_vector),
            source=source,
            message="레시피가 추천 풀에 편입되었습니다."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"레시피 등록 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 레시피 제작 가능성 검토 API
# =====================================================

@app.post("/api/recipe/validate", response_model=RecipeValidateResponse)
async def recipe_validate(request: RecipeValidateRequest):
    """
    레시피 제작 가능성 검토 (Gemini 양조 전문가 분석)

    Args:
        request: 레시피 검토 요청

    Returns:
        feasibility, score, issues, suggestions, summary
    """
    if not GEMINI_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI 서비스 점검 중입니다. 잠시 후 다시 시도해주세요.")
    try:
        cache_key = f"recipe_validate_{hash(request.title + request.main_ingredient + ''.join(sorted(request.sub_ingredients)))}"
        cached = get_cache(cache_key)
        if cached is not None:
            logger.info(f"레시피 검토 캐시 히트: {request.title}")
            return RecipeValidateResponse(**cached, cached=True)

        recipe_ai = app.state.recipe_ai
        result = await recipe_ai.validate_recipe(
            title=request.title,
            main_ingredient=request.main_ingredient,
            sub_ingredients=request.sub_ingredients,
            abv_range=request.abv_range,
            flavor_tags=request.flavor_tags,
            description=request.description
        )

        set_cache(cache_key, result, ttl_minutes=60)
        return RecipeValidateResponse(**result)

    except Exception as e:
        raise_api_error(e, "레시피 검토 중 오류가 발생했습니다.")


@app.post("/api/image/generate")
async def generate_image(request: ImageGenerateRequest):
    """전통주 이미지 생성 (Gemini 프롬프트 + Stable Diffusion)"""
    if not GEMINI_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI 서비스 점검 중입니다.")
    result = await _image_generator.generate(
        name=request.name,
        description=request.description,
        flavor_tags=request.flavor_tags,
        region=request.region
    )
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
