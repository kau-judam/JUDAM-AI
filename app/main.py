"""
주담 AI 서버 - FastAPI 진입점
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
from pathlib import Path
import os

# 기존 모듈 임포트
from app.core.recommender import AdvancedMakgeolliRecommender
from app.core.survey_converter import SurveyToVectorConverter, SurveyResponse
from app.law_client import LawClient, ContentType, FilterResult
from app.insight import InsightDashboard, InsightRequest, InsightResponse
from app.rag import TraditionalAlcoholRAG, RAGSearchRequest, RAGSearchResponse
from app.models import (
    TasteVector, RecommendRequest, RecommendResponse,
    TasteUpdateRequest, TasteUpdateResponse,
    TasteHistorySummaryResponse,
    FoodRecommendRequest, FoodRecommendResponse,
    SurveyConvertResponse, HealthResponse,
    LawFilterRequest
)

# 추천 시스템 초기화
_recommender = AdvancedMakgeolliRecommender()
_survey_converter = SurveyToVectorConverter()
_law_client = LawClient()
_insight_dashboard = InsightDashboard()
_rag_system = TraditionalAlcoholRAG()

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


# 헬퍼 함수
def clean_string(value) -> str:
    """NaN 또는 None을 빈 문자열로 변환"""
    if value is None or (isinstance(value, float) and str(value) == 'nan'):
        return ""
    return str(value) if value else ""


# Pydantic 모델
class TasteVector(BaseModel):
    """맛 벡터 모델"""
    sweetness: float
    body: float
    carbonation: float
    flavor: float
    alcohol: float
    acidity: float
    aroma_intensity: float
    finish: float


class RecommendRequest(BaseModel):
    """추천 요청 모델"""
    user_vector: TasteVector
    top_k: int = 10
    exclude_ids: List[str] = []


class RecommendResponse(BaseModel):
    """추천 응답 모델"""
    id: str
    name: str
    similarity: float
    abv: float
    brewery: str
    region: str
    features: str
    taste_vector: TasteVector


class TasteUpdateRequest(BaseModel):
    """취향 업데이트 요청 모델"""
    user_id: str
    drink_id: str
    rating: int
    tags: List[str] = []


class FoodRecommendRequest(BaseModel):
    """음식 기반 추천 요청 모델"""
    food: str
    top_k: int = 5


class FoodRecommendResponse(BaseModel):
    """음식 기반 추천 응답 모델"""
    id: str
    name: str
    abv: float
    brewery: str
    region: str
    features: str
    taste_vector: TasteVector
    reason: str


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
            "law_filter": "/api/law/filter",
            "law_info": "/api/law/info",
            "insight": "/api/insight",
            "rag_search": "/api/rag/search",
            "health": "/health"
        }
    }


@app.get("/health")
def health():
    """헬스체크 엔드포인트"""
    try:
        recommender = app.state.recommender
        api_key = os.getenv("GEMINI_API_KEY")

        return {
            "status": "ok",
            "data_count": len(recommender.drinks),
            "user_count": len(recommender.user_taste_history),
            "gemini_key_loaded": bool(api_key)
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
                taste_vector=TasteVector(**rec['taste_vector'])
            ))

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/taste/update")
def taste_update(request: TasteUpdateRequest):
    """
    사용자 취향 업데이트

    Args:
        request: 취향 업데이트 요청

    Returns:
        업데이트 결과
    """
    try:
        recommender = app.state.recommender

        recommender.update_user_taste(
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
        vector = TasteVector(**vector_dict)

        return SurveyConvertResponse(
            status="success",
            taste_vector=vector
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
def get_insights(period: str = "week"):
    """
    인사이트 대시보드

    Args:
        period: 기간 (day, week, month)

    Returns:
        인사이트 결과
    """
    try:
        insight_dashboard = app.state.insight_dashboard

        insights = insight_dashboard.get_insights(period=period)

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
