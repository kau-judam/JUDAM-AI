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
    match_reason: List[str] = []

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
    """술BTI 25문항 설문 응답 모델"""

    # q1~q3: 서열척도 (1~5)
    q1: int = Field(..., ge=1, le=5, description="전통주 경험 수준 (1~5)")
    q2: int = Field(..., ge=1, le=5, description="선호 도수 수준 (1~5)")
    q3: int = Field(..., ge=1, le=5, description="선호 바디감/색상 수준 (1~5)")

    # q4~q22: 등간척도 Likert (1~7)
    q4: int = Field(..., ge=1, le=7, description="단맛 선호도 (1~7)")
    q5: int = Field(..., ge=1, le=7, description="신맛 선호도 (1~7)")
    q6: int = Field(..., ge=1, le=7, description="청량감 선호도 (1~7)")
    q7: int = Field(..., ge=1, le=7, description="과일 향 선호도 (1~7)")
    q8: int = Field(..., ge=1, le=7, description="여운 선호도 (1~7)")
    q9: int = Field(..., ge=1, le=7, description="풍미 복잡성 선호도 (1~7)")
    q10: int = Field(..., ge=1, le=7, description="바디감 선호도 (1~7)")
    q11: int = Field(..., ge=1, le=7, description="맛의 농도 선호도 (1~7)")
    q12: int = Field(..., ge=1, le=7, description="도수 내성 (1~7)")
    q13: int = Field(..., ge=1, le=7, description="알콜 감지 선호도 (1~7)")
    q14: int = Field(..., ge=1, le=7, description="탄산감 선호도 (1~7)")
    q15: int = Field(..., ge=1, le=7, description="향기 강도 선호도 (1~7)")
    q16: int = Field(..., ge=1, le=7, description="꽃향 선호도 (1~7)")
    q17: int = Field(..., ge=1, le=7, description="허브향 선호도 (1~7)")
    q18: int = Field(..., ge=1, le=7, description="과일향 선호도 (1~7)")
    q19: int = Field(..., ge=1, le=7, description="신선한 향 선호도 (1~7)")
    q20: int = Field(..., ge=1, le=7, description="구수한 향 선호도 (1~7)")
    q21: int = Field(..., ge=1, le=7, description="알콜 향 선호도 (1~7)")
    q22: int = Field(..., ge=1, le=7, description="전반적인 맛 강도 선호도 (1~7)")

    # q23: 명목척도 (1~5) - 선호 과일
    q23: int = Field(..., ge=1, le=5, description="선호 과일 (1~5)")

    # q24: 명목척도 복수선택 - 음식 페어링
    q24: List[int] = Field(..., description="음식 페어링 선호 (복수선택)")

    # q25: 명목척도 복수선택 - 관심 향
    q25: List[int] = Field(..., description="관심 향 (복수선택)")


class SurveyConvertResponse(BaseModel):
    """설문 변환 응답 모델"""
    status: str
    taste_vector: Dict[str, float]
    food_pairing: List[str] = []


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


# ========== 술BTI 관련 ==========

class BTITypeRequest(BaseModel):
    """술BTI 유형 판정 요청 모델"""
    sweetness: float = Field(..., ge=0, le=10, description="단맛 (0~10)")
    body: float = Field(..., ge=0, le=10, description="바디감 (0~10)")
    carbonation: float = Field(..., ge=0, le=10, description="탄산 (0~10)")
    flavor: float = Field(..., ge=0, le=10, description="풍미 (0~10)")


class BTITypeResponse(BaseModel):
    """술BTI 유형 판정 응답 모델"""
    code: str
    character_name: str
    tags: List[str]
    recommended_drinks: List[str]


# ========== 레시피 관련 ==========

class SubIngredientsRequest(BaseModel):
    """서브재료 추천 요청 모델"""
    main_ingredient: str = Field(..., description="메인 재료")
    region: str = Field(..., description="지역")


class SubIngredientsResponse(BaseModel):
    """서브재료 추천 응답 모델"""
    sub_ingredients: List[str]


class FlavorTagsRequest(BaseModel):
    """맛 태그 추천 요청 모델"""
    title: str = Field(..., description="제목")
    main_ingredient: str = Field(..., description="메인 재료")
    sub_ingredients: List[str] = Field(default_factory=list, description="서브 재료")
    abv_range: str = Field(..., description="도수 범위")


class FlavorTagsResponse(BaseModel):
    """맛 태그 추천 응답 모델"""
    flavor_tags: List[str]


class SummaryRequest(BaseModel):
    """요약문 생성 요청 모델"""
    title: str = Field(..., description="제목")
    main_ingredient: str = Field(..., description="메인 재료")
    sub_ingredients: List[str] = Field(default_factory=list, description="서브 재료")
    abv_range: str = Field(..., description="도수 범위")
    flavor_tags: List[str] = Field(default_factory=list, description="맛 태그")
    concept: Optional[str] = Field(None, description="컨셉")


class SummaryResponse(BaseModel):
    """요약문 생성 응답 모델"""
    summary: str


# ========== 설문→추천 원스텝 관련 ==========

class SurveyRecommendItem(BaseModel):
    """설문→추천 결과 개별 항목"""
    id: str
    name: str
    similarity: float
    abv: float
    brewery: Optional[str]
    region: Optional[str]
    features: Optional[str]
    taste_vector: TasteVector
    match_reason: List[str] = []


class SurveyRecommendResponse(BaseModel):
    """설문→추천 원스텝 응답 모델"""
    status: str
    taste_vector: Dict[str, float]
    food_pairing: List[str] = []
    recommendations: List[SurveyRecommendItem]
