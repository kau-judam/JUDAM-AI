# 주담 AI 서버 API 가이드

백엔드 Node.js 팀원용 AI 서버 연동 문서

## 서버 정보

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`

## 서버 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정 (.env 파일)
GEMINI_API_KEY=your_gemini_api_key
LAW_API_KEY=your_law_api_key
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/juddam
REDIS_URL=redis://localhost:6379

# 3. 서버 실행
uvicorn app.main:app --reload --port 8000
```

---

## API 목록

### 1. POST /api/recommend

맛 벡터 기반 전통주 추천

#### 요청

```json
{
  "user_vector": {
    "sweetness": 7.5,
    "body": 4.0,
    "carbonation": 8.0,
    "flavor": 6.5,
    "alcohol": 3.0,
    "acidity": 5.0,
    "aroma_intensity": 7.0,
    "finish": 4.5
  },
  "top_k": 10,
  "exclude_ids": []
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| user_vector | object | 사용자 맛 벡터 (0~10) |
| top_k | number | 추천할 상위 k개 (1~50) |
| exclude_ids | string[] | 제외할 전통주 ID 리스트 |

#### 응답

```json
[
  {
    "id": "drink_001",
    "name": "복순도가 복분자주",
    "similarity": 0.92,
    "abv": 15.0,
    "brewery": "복순도가",
    "region": "경기도",
    "features": "복분자의 달콤함과 풍부한 향",
    "taste_vector": {
      "sweetness": 8.0,
      "body": 5.0,
      "carbonation": 2.0,
      "flavor": 9.0,
      "alcohol": 7.0,
      "acidity": 6.0,
      "aroma_intensity": 8.5,
      "finish": 5.0
    }
  }
]
```

#### Node.js 예시

```javascript
const response = await fetch('http://localhost:8000/api/recommend', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_vector: {
      sweetness: 7.5,
      body: 4.0,
      carbonation: 8.0,
      flavor: 6.5,
      alcohol: 3.0,
      acidity: 5.0,
      aroma_intensity: 7.0,
      finish: 4.5
    },
    top_k: 10,
    exclude_ids: []
  })
});

const recommendations = await response.json();
```

---

### 2. POST /api/survey/convert

술BTI 설문 응답 → 맛 벡터 변환

#### 요청

```json
{
  "sweetness": 7,
  "body": 4,
  "carbonation": 8,
  "flavor": 6,
  "alcohol": 3,
  "preferred_ingredients": ["쌀", "과일"],
  "disliked_ingredients": ["매운맛"],
  "preferred_region": "경기도"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| sweetness | number | 단맛 선호도 (0~10) |
| body | number | 바디감 선호도 (0~10) |
| carbonation | number | 탄산 선호도 (0~10) |
| flavor | number | 풍미 선호도 (0~10) |
| alcohol | number | 도수 선호도 (0~10) |
| preferred_ingredients | string[] | 선호하는 재료 |
| disliked_ingredients | string[] | 싫어하는 재료 |
| preferred_region | string | 선호하는 지역 |

#### 응답

```json
{
  "status": "success",
  "taste_vector": {
    "sweetness": 7.5,
    "body": 4.0,
    "carbonation": 8.0,
    "flavor": 6.5,
    "alcohol": 3.0,
    "acidity": 5.0,
    "aroma_intensity": 7.0,
    "finish": 4.5
  }
}
```

#### Node.js 예시

```javascript
const response = await fetch('http://localhost:8000/api/survey/convert', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    sweetness: 7,
    body: 4,
    carbonation: 8,
    flavor: 6,
    alcohol: 3,
    preferred_ingredients: ["쌀", "과일"],
    disliked_ingredients: ["매운맛"],
    preferred_region: "경기도"
  })
});

const result = await response.json();
```

---

### 3. POST /api/law/filter

콘텐츠 법률 필터링 (청소년보호법, 식품위생법, 자본시장법 등)

#### 요청

```json
{
  "content_type": "recipe",
  "title": "전통 막걸리 레시피",
  "description": "쌀과 누룩으로 만드는 전통 막걸리 제조 방법",
  "ingredients": ["쌀", "누룩", "물"],
  "target_region": "경기도"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| content_type | string | 콘텐츠 타입 (recipe, funding) |
| title | string | 제목 |
| description | string | 설명 |
| ingredients | string[] | 재료 리스트 |
| target_region | string? | 타겟 지역 |

#### 응답

```json
{
  "violation": false,
  "details": [],
  "recommendation": "법적 문제가 없습니다."
}
```

위반 시 응답:

```json
{
  "violation": true,
  "details": [
    {
      "category": "미성년자 타겟",
      "law": "청소년보호법",
      "reason": "미성년자에게 주류 판매 금지",
      "article": "제10조"
    }
  ],
  "recommendation": "다음 문제를 수정해주세요: 미성년자에게 주류 판매 금지"
}
```

#### Node.js 예시

```javascript
const response = await fetch('http://localhost:8000/api/law/filter', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    content_type: "recipe",
    title: "전통 막걸리 레시피",
    description: "쌀과 누룩으로 만드는 전통 막걸리 제조 방법",
    ingredients: ["쌀", "누룩", "물"],
    target_region: "경기도"
  })
});

const result = await response.json();

if (result.violation) {
  console.log("법적 문제가 있습니다:", result.details);
} else {
  console.log("법적 문제가 없습니다.");
}
```

---

### 4. GET /api/insight

인사이트 대시보드 (집계 + 예측 + 군집화)

#### 요청

```
GET /api/insight?period=week
```

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| period | string | 기간 (day, week, month) |

#### 응답

```json
{
  "period": "week",
  "summary": "이번 주 전통주 관심도가 15% 증가했습니다.",
  "statistics": {
    "total_views": 1250,
    "total_favorites": 320,
    "top_region": "경기도",
    "avg_rating": 4.2
  },
  "predictions": {
    "next_week_views": 1437,
    "trend": "increasing"
  },
  "clusters": [
    {
      "id": 0,
      "name": "단맛 선호",
      "count": 45,
      "characteristics": ["높은 단맛", "낮은 도수"]
    }
  ]
}
```

#### Node.js 예시

```javascript
const response = await fetch('http://localhost:8000/api/insight?period=week');
const insights = await response.json();

console.log("요약:", insights.summary);
console.log("예측:", insights.predictions);
```

---

## 에러 코드

| 코드 | 설명 |
|------|------|
| 200 | 성공 |
| 422 | 요청 데이터 검증 실패 (필수 필드 누락, 타입 불일치 등) |
| 500 | 서버 내부 오류 |

### 422 에러 예시

```json
{
  "detail": [
    {
      "loc": ["body", "user_vector", "sweetness"],
      "msg": "ensure this value is greater than or equal to 0",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

### 500 에러 예시

```json
{
  "detail": "GEMINI_API_KEY가 설정되지 않았습니다."
}
```

---

## 추가 API

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| /api/taste/update | POST | 사용자 취향 업데이트 |
| /api/taste/history/{user_id} | GET | 사용자 취향 히스토리 조회 |
| /api/food/recommend | POST | 음식 기반 추천 |
| /api/law/info | GET | 법령 정보 조회 |
| /api/rag/search | POST | RAG 문서 검색 |
| /health | GET | 헬스체크 |

---

## 개발 참고

### 맛 벡터 구조

```typescript
interface TasteVector {
  sweetness: number;      // 단맛 (0~10)
  body: number;           // 바디감 (0~10)
  carbonation: number;    // 탄산 (0~10)
  flavor: number;         // 풍미 (0~10)
  alcohol: number;        // 도수 (0~10)
  acidity: number;        // 산미 (0~10)
  aroma_intensity: number; // 향기 강도 (0~10)
  finish: number;         // 여운 (0~10)
}
```

### 법률 필터링 위반 카테고리

- 미성년자 타겟 (청소년보호법)
- 불법/금지 재료 (식품위생법)
- 지역특산주 요건 불충족 (전통주등의산업진흥에관한법률)
- 과대광고/허위표시 (식품위생법, 표시광고법)
- 무허가 제조 방법 (주세법)
- 도수 표기 비현실적 (주세법)
- 상표명 침해 가능성 (상표법)
- 펀딩 금융 규제 위반 (자본시장법)
