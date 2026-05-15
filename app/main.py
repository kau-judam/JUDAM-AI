"""
주담 AI 서버 - FastAPI 진입점
"""

import logging
import os
from fastapi import FastAPI, HTTPException
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
from app.chat import router as chat_router
from app.models import (
    TasteVector, RecommendRequest, RecommendResponse,
    TasteUpdateRequest, TasteUpdateResponse,
    TasteHistorySummaryResponse,
    FoodRecommendRequest, FoodRecommendResponse,
    HealthResponse,
    LawFilterRequest,
    SurveyConvertResponse,
    BTITypeRequest, BTITypeResponse,
    SubIngredientsRequest, SubIngredientsResponse,
    FlavorTagsRequest, FlavorTagsResponse,
    SummaryRequest, SummaryResponse,
    SurveyRecommendResponse, SurveyRecommendItem
)
from app.db import db

# 추천 시스템 초기화
_recommender = AdvancedMakgeolliRecommender()
_survey_converter = SurveyToVectorConverter()
_law_client = LawClient()
_insight_dashboard = InsightDashboard()
_rag_system = TraditionalAlcoholRAG()
_recipe_ai = RecipeAI()

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


def determine_bti_code(sweetness: float, body: float, carbonation: float, flavor: float) -> str:
    """
    맛 벡터에서 술BTI 코드 판정

    Args:
        sweetness: 단맛 (0~10)
        body: 바디감 (0~10)
        carbonation: 탄산 (0~10)
        flavor: 풍미 (0~10)

    Returns:
        4자리 술BTI 코드 (예: SHMC)
    """
    # S/D: sweetness >= 5 → S (Sweet), < 5 → D (Dry)
    s_d = 'S' if sweetness >= 5 else 'D'

    # H/L: body >= 5 → H (Heavy), < 5 → L (Light)
    h_l = 'H' if body >= 5 else 'L'

    # F/M: carbonation >= 5 → F (Fizzy), < 5 → M (Mellow)
    f_m = 'F' if carbonation >= 5 else 'M'

    # C/U: flavor >= 5 → U (Unique), < 5 → C (Classic)
    c_u = 'U' if flavor >= 5 else 'C'

    return f"{s_d}{h_l}{f_m}{c_u}"


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
            "survey_bti_type": "/api/survey/bti-type",
            "recipe_suggest_sub_ingredients": "/api/recipe/suggest-sub-ingredients",
            "recipe_suggest_flavor_tags": "/api/recipe/suggest-flavor-tags",
            "recipe_suggest_summary": "/api/recipe/suggest-summary",
            "law_filter": "/api/law/filter",
            "law_info": "/api/law/info",
            "insight": "/api/insight",
            "rag_search": "/api/rag/search",
            "rag_category": "/api/rag/category/{category}",
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

        # 기능별 상태 판정
        recommend_ok = "ok" if len(recommender.drinks) > 0 else "no_data"
        recipe_ok    = "ok" if api_key else "no_gemini_key"
        law_ok       = "ok" if api_key else "no_gemini_key"   # Gemini 분석 의존
        chat_ok      = "ok" if api_key else "no_gemini_key"
        insight_ok   = "ok" if len(recommender.drinks) > 0 else "no_data"

        return {
            "status": "ok",
            "data_count": len(recommender.drinks),
            "user_count": len(recommender.user_taste_history),
            "gemini_key_loaded": bool(api_key),
            "law_key_loaded": bool(law_key),
            "db_connected": recommender.db_connected,
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
def recommend(request: RecommendRequest):
    """
    맛 벡터 기반 추천

    Args:
        request: 추천 요청

    Returns:
        추천 결과 리스트
    """
    try:
        recommender = app.state.recommender

        # 맛 벡터 변환
        user_vector = request.user_vector.model_dump()

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
                abv=rec['abv'],
                brewery=clean_string(rec.get('brewery')),
                region=clean_string(rec.get('region')),
                features=clean_string(rec.get('features')),
                taste_vector=TasteVector(**rec['taste_vector']),
                match_reason=rec.get('match_reason', [])
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
    try:
        recommender = app.state.recommender

        await recommender.update_user_taste(
            user_id=request.user_id,
            drink_id=request.drink_id,
            rating=request.rating,
            tags=request.tags
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
    try:
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

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/survey/convert")
def survey_convert(survey: SurveyResponse):
    """
    술BTI 설문 → 맛 벡터 변환

    Args:
        survey: 설문 응답

    Returns:
        맛 벡터
    """
    try:
        survey_converter = app.state.survey_converter
        vector_dict = survey_converter.convert(survey)
        if hasattr(vector_dict, 'model_dump'):
            vector_dict = vector_dict.model_dump()
        food_pairing = vector_dict.pop('food_pairing', []) if isinstance(vector_dict, dict) else []
        return {"status": "success", "taste_vector": vector_dict, "food_pairing": food_pairing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/survey/recommend", response_model=SurveyRecommendResponse)
def survey_recommend(survey: SurveyResponse):
    """
    술BTI 설문 → 맛 벡터 변환 + 추천 원스텝 API

    Args:
        survey: 25문항 설문 응답 (survey/convert와 동일)

    Returns:
        taste_vector + top 5 추천 결과 (match_reason 포함)
    """
    try:
        survey_converter = app.state.survey_converter
        recommender = app.state.recommender

        # 1단계: 설문 → 맛 벡터 변환
        vector_dict = survey_converter.convert(survey)
        if hasattr(vector_dict, 'model_dump'):
            vector_dict = vector_dict.model_dump()
        food_pairing = vector_dict.pop('food_pairing', []) if isinstance(vector_dict, dict) else []

        # 2단계: 맛 벡터 → 추천 (top_k=5)
        recommendations = recommender.recommend(user_vector=vector_dict, top_k=5)

        # 응답 조립
        rec_items = [
            SurveyRecommendItem(
                id=rec['id'],
                name=rec['name'],
                similarity=rec['similarity'],
                abv=rec['abv'],
                brewery=clean_string(rec.get('brewery')),
                region=clean_string(rec.get('region')),
                features=clean_string(rec.get('features')),
                taste_vector=TasteVector(**rec['taste_vector']),
                match_reason=rec.get('match_reason', [])
            )
            for rec in recommendations
        ]

        return SurveyRecommendResponse(
            status="success",
            taste_vector=vector_dict,
            food_pairing=food_pairing,
            recommendations=rec_items
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/survey/bti-type", response_model=BTITypeResponse)
def get_bti_type(request: BTITypeRequest):
    """
    맛 벡터 기반 술BTI 유형 판정

    Args:
        request: 맛 벡터 요청

    Returns:
        술BTI 유형 정보
    """
    try:
        # 술BTI 코드 판정
        code = determine_bti_code(
            sweetness=request.sweetness,
            body=request.body,
            carbonation=request.carbonation,
            flavor=request.flavor
        )

        # 유형 정보 조회
        type_info = BTI_TYPE_MAPPING.get(code, {
            "name": "알 수 없는 유형",
            "tags": [],
            "drinks": []
        })

        return BTITypeResponse(
            code=code,
            character_name=type_info["name"],
            tags=type_info["tags"],
            recommended_drinks=type_info["drinks"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recipe/suggest-sub-ingredients", response_model=SubIngredientsResponse)
async def suggest_sub_ingredients(request: SubIngredientsRequest):
    """
    서브재료 추천

    Args:
        request: 서브재료 추천 요청

    Returns:
        서브재료 리스트
    """
    try:
        recipe_ai = app.state.recipe_ai

        result = await recipe_ai.suggest_sub_ingredients(
            main_ingredient=request.main_ingredient,
            region=request.region
        )

        return SubIngredientsResponse(sub_ingredients=result["sub_ingredients"])

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
    try:
        law_client = app.state.law_client

        # 콘텐츠 타입 변환
        ct = ContentType.RECIPE if request.content_type == "recipe" else ContentType.FUNDING

        result = await law_client.filter_content(
            title=request.title,
            description=request.description,
            ingredients=request.ingredients,
            content_type=ct
        )

        return {
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
        rag_system = app.state.rag_system

        results = rag_system.search(
            query=request.query,
            top_k=request.top_k,
            category=request.category
        )

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/category/{category}")
def get_rag_documents_by_category(category: str):
    """
    카테고리별 RAG 문서 조회

    Args:
        category: 카테고리

    Returns:
        문서 리스트
    """
    try:
        rag_system = app.state.rag_system

        docs = rag_system.get_documents_by_category(category)

        return {
            "status": "success",
            "category": category,
            "documents": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "source": doc.source,
                    "metadata": doc.metadata
                }
                for doc in docs
            ],
            "total": len(docs)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
