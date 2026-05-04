"""
Pydantic 모델
요청/응답 데이터 검증용 모델
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from datetime import datetime


# ========== 맛 벡터 관련 ==========

class TasteVector(BaseModel):
    """맛 벡터 모델"""
    sweetness: float = Field(..., ge=0, le=10, description="단맛 (0~10)")
    body: float = Field(..., ge=0, le=10, description="바디감 (0~10)")
    carbonation: float = Field(..., ge=0, le=10, description="탄산 (0~10)")
    flavor: float = Field(..., ge=0, le=10, description="풍미 (0~10)")
    alcohol: float = Field(..., ge=0, le=10, description="도수 (0~10)")
    acidity: float = Field(..., ge=0, le=10, description="산미 (0~10)")
    aroma_intensity: float = Field(..., ge=0, le=10, description="향기 강도 (0~10)")
    finish: float = Field(..., ge=0, le=10, description="여운 (0~10)")

    @validator('*')
    def round_values(cls, v):
        """소수점 둘째 자리까지 반올림"""
        return round(v, 2)


# ========== 전통주 관련 ==========

class DrinkBase(BaseModel):
    """전통주 기본 모델"""
    name: str = Field(..., min_length=1, max_length=100, description="전통주 이름")
    abv: float = Field(..., ge=0, le=100, description="알콜 도수 (%)")
    brewery: Optional[str] = Field(None, max_length=100, description="양조장")
    region: Optional[str] = Field(None, max_length=50, description="지역")
    description: Optional[str] = Field(None, description="설명")
    features: Optional[str] = Field(None, description="특징")
    ingredients: Optional[str] = Field(None, description="원재료")
    awards: Optional[str] = Field(None, description="수상 이력")


class DrinkCreate(DrinkBase):
    """전통주 생성 모델"""
    taste_vector: TasteVector


class DrinkUpdate(DrinkBase):
    """전통주 수정 모델"""
    taste_vector: Optional[TasteVector] = None


class DrinkResponse(DrinkBase):
    """전통주 응답 모델"""
    id: str
    taste_vector: TasteVector
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DrinkListItem(BaseModel):
    """전통주 리스트 아이템 모델"""
    id: str
    name: str
    abv: float
    brewery: Optional[str]
    region: Optional[str]
    similarity: Optional[float] = None

    class Config:
        from_attributes = True


# ========== 사용자 관련 ==========

class UserBase(BaseModel):
    """사용자 기본 모델"""
    name: Optional[str] = Field(None, max_length=100, description="이름")
    email: Optional[str] = Field(None, max_length=100, description="이메일")


class UserCreate(UserBase):
    """사용자 생성 모델"""
    id: str = Field(..., min_length=1, max_length=50, description="사용자 ID")


class UserUpdate(UserBase):
    """사용자 수정 모델"""
    pass


class UserResponse(UserBase):
    """사용자 응답 모델"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== 취향 히스토리 관련 ==========

class TasteHistoryCreate(BaseModel):
    """취향 히스토리 생성 모델"""
    user_id: str = Field(..., min_length=1, max_length=50, description="사용자 ID")
    drink_id: str = Field(..., min_length=1, max_length=50, description="전통주 ID")
    rating: int = Field(..., ge=1, le=5, description="별점 (1~5)")
    tags: List[str] = Field(default_factory=list, description="태그")
    taste_vector: Optional[TasteVector] = None


class TasteHistoryResponse(BaseModel):
    """취향 히스토리 응답 모델"""
    id: int
    user_id: str
    drink_id: str
    rating: int
    tags: List[str]
    taste_vector: Optional[TasteVector]
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 추천 관련 ==========

class RecommendRequest(BaseModel):
    """추천 요청 모델"""
    user_vector: TasteVector
    top_k: int = Field(10, ge=1, le=50, description="추천할 상위 k개")
    exclude_ids: List[str] = Field(default_factory=list, description="제외할 ID 리스트")
    weights: Optional[Dict[str, float]] = Field(
        None,
        description="가중치 (taste, ingredient, region)"
    )


class RecommendResponse(BaseModel):
    """추천 응답 모델"""
    id: str
    name: str
    similarity: float
    abv: float
    brewery: Optional[str]
    region: Optional[str]
    features: Optional[str]
    taste_vector: TasteVector

    class Config:
        from_attributes = True


class TasteUpdateRequest(BaseModel):
    """취향 업데이트 요청 모델"""
    user_id: str = Field(..., min_length=1, max_length=50, description="사용자 ID")
    drink_id: str = Field(..., min_length=1, max_length=50, description="전통주 ID")
    rating: int = Field(..., ge=1, le=5, description="별점 (1~5)")
    tags: List[str] = Field(default_factory=list, description="태그")


class TasteUpdateResponse(BaseModel):
    """취향 업데이트 응답 모델"""
    status: str
    message: str


class TasteHistorySummaryResponse(BaseModel):
    """취향 히스토리 요약 응답 모델"""
    user_id: str
    history_count: int
    history: List[TasteHistoryResponse]
    evolved_taste_vector: TasteVector


# ========== 음식 기반 추천 관련 ==========

class FoodRecommendRequest(BaseModel):
    """음식 기반 추천 요청 모델"""
    food: str = Field(..., min_length=1, description="음식 이름")
    top_k: int = Field(5, ge=1, le=20, description="추천할 상위 k개")


class FoodRecommendResponse(BaseModel):
    """음식 기반 추천 응답 모델"""
    id: str
    name: str
    abv: float
    brewery: Optional[str]
    region: Optional[str]
    features: Optional[str]
    taste_vector: TasteVector
    reason: str

    class Config:
        from_attributes = True


# ========== 설문 관련 ==========

class SurveyResponse(BaseModel):
    """술BTI 설문 응답 모델"""
    sweetness: int = Field(..., ge=0, le=10, description="단맛 선호도 (0~10)")
    body: int = Field(..., ge=0, le=10, description="바디감 선호도 (0~10)")
    carbonation: int = Field(..., ge=0, le=10, description="탄산 선호도 (0~10)")
    flavor: int = Field(..., ge=0, le=10, description="풍미 선호도 (0~10)")
    alcohol: int = Field(..., ge=0, le=10, description="도수 선호도 (0~10)")
    preferred_ingredients: List[str] = Field(default_factory=list, description="선호하는 재료")
    disliked_ingredients: List[str] = Field(default_factory=list, description="싫어하는 재료")
    preferred_region: str = Field("", max_length=50, description="선호하는 지역")


class SurveyConvertResponse(BaseModel):
    """설문 변환 응답 모델"""
    status: str
    taste_vector: TasteVector


# ========== 법률 필터링 관련 ==========

class LawFilterRequest(BaseModel):
    """법률 필터링 요청 모델"""
    content_type: str = Field(..., description="콘텐츠 타입 (recipe, funding)")
    title: str = Field(..., min_length=1, description="제목")
    description: str = Field(..., min_length=1, description="설명")
    ingredients: List[str] = Field(default_factory=list, description="재료 리스트")
    target_region: Optional[str] = Field(None, description="타겟 지역")


class LawFilterResponse(BaseModel):
    """법률 필터링 응답 모델"""
    status: str
    query: str
    laws: List[Dict]
    summary: str
    relevant: bool


# ========== 인사이트 관련 ==========

class InsightRequest(BaseModel):
    """인사이트 요청 모델"""
    period: str = Field("week", description="기간 (day, week, month)")
    category: Optional[str] = Field(None, description="카테고리")


class InsightResponse(BaseModel):
    """인사이트 응답 모델"""
    period: str
    summary: str
    statistics: Dict
    predictions: Dict
    clusters: List[Dict]


# ========== RAG 관련 ==========

class RAGDocument(BaseModel):
    """RAG 문서 모델"""
    id: str
    title: str
    content: str
    source: str
    category: str
    metadata: Dict


class RAGSearchRequest(BaseModel):
    """RAG 검색 요청 모델"""
    query: str = Field(..., min_length=1, description="검색 쿼리")
    top_k: int = Field(5, ge=1, le=20, description="반환할 상위 k개")
    category: Optional[str] = Field(None, description="카테고리")


class RAGSearchResponse(BaseModel):
    """RAG 검색 응답 모델"""
    query: str
    results: List[Dict]
    total: int


# ========== 공통 응답 모델 ==========

class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    data_count: Optional[int] = None
    user_count: Optional[int] = None
    gemini_key_loaded: Optional[bool] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    status: str = "error"
    message: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    """성공 응답 모델"""
    status: str = "success"
    message: str
    data: Optional[Dict] = None
