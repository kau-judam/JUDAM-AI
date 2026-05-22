# 주담 AI 서버 API 가이드

## 서버 정보

| 환경 | URL |
|------|-----|
| 로컬 개발 | http://localhost:8000 |
| EC2 (직접) | http://43.202.24.223:8000 |
| EC2 프록시 | http://43.202.24.223:3000/api/ai |
| Swagger UI | http://localhost:8000/docs (로컬만) |

## 공통 사항

- **Content-Type**: `application/json`
- **에러 형식**: `{ "status": "error", "message": "에러 메시지" }`
- **Gemini 429 초과**: HTTP 503 반환 — "현재 AI 서비스가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요."
- **GEMINI_AVAILABLE=false**: HTTP 503 반환 — "AI 서비스 점검 중입니다. 잠시 후 다시 시도해주세요."
- **404**: `{ "status": "error", "message": "요청한 경로를 찾을 수 없습니다." }`

---

## 목차

1. [GET /health](#1-get-health)
2. [POST /api/recommend](#2-post-apirecommend)
3. [POST /api/survey/convert](#3-post-apisurveyconvert)
4. [GET /api/taste/profile/{user_id}](#4-get-apitasteprofileuser_id)
5. [POST /api/taste/update](#5-post-apitasteupdate)
6. [GET /api/taste/history/{user_id}](#6-get-apitastehistoryuser_id)
7. [POST /api/chat](#7-post-apichat)
8. [POST /api/food/recommend](#8-post-apifoodrecommend)
9. [POST /api/recipe/suggest-sub-ingredients](#9-post-apirecipesuggest-sub-ingredients)
10. [POST /api/recipe/suggest-flavor-tags](#10-post-apirecipesuggest-flavor-tags)
11. [POST /api/recipe/suggest-summary](#11-post-apirecipesuggest-summary)
12. [POST /api/law/filter](#12-post-apilawfilter)
13. [GET /api/law/info](#13-get-apilawinfo)
14. [GET /api/insight](#14-get-apiinsight)
15. [POST /api/rag/search](#15-post-apiragsearch)
16. [POST /api/crawler/check](#16-post-apicrawlercheck)
17. [POST /api/drinks/request](#17-post-apidrinksrequest)
18. [GET /api/drinks/requests](#18-get-apidrinksrequests)
19. [POST /api/drinks/requests/{id}/approve](#19-post-apidrinksrequestsidapprove)
20. [POST /api/funding/register](#20-post-apifundingregister)
21. [GET /api/funding/{funding_id}](#21-get-apifundingfunding_id)
22. [POST /api/funding/{funding_id}/taste-update](#22-post-apifundingfunding_idtaste-update)
23. [POST /api/recipe/register](#23-post-apireciperegister)
24. [POST /api/recipe/validate](#24-post-apirecipevalidate)

---

## 1. GET /health

서버 상태 및 API별 동작 여부 확인.

### Response

```json
{
  "status": "ok",
  "version": "0.3.0",
  "data_count": 207,
  "funding_count": 1,
  "recipe_count": 0,
  "user_count": 1,
  "gemini_key_loaded": true,
  "gemini_available": true,
  "law_key_loaded": true,
  "db_connected": false,
  "uptime_seconds": 3600,
  "api_status": {
    "recommend": "ok",
    "recipe": "ok",
    "law": "ok",
    "chat": "ok",
    "insight": "ok"
  }
}
```

> `recipe` / `law` / `chat`은 `GEMINI_AVAILABLE=false`일 때 `"limited"` 반환.

| 필드 | 타입 | 설명 |
|------|------|------|
| status | string | 서버 상태 ("ok" / "error") |
| version | string | 서버 버전 |
| data_count | number | 로드된 전통주 수 (기본 데이터 + 펀딩/레시피 포함) |
| funding_count | number | 등록된 펀딩 전통주 수 |
| recipe_count | number | 등록된 레시피 수 |
| user_count | number | 저장된 사용자 프로필 수 |
| gemini_key_loaded | boolean | Gemini API 키 로드 여부 |
| gemini_available | boolean | Gemini 호출 가능 여부 (한도 초과 시 false) |
| law_key_loaded | boolean | 법령 API 키 로드 여부 |
| db_connected | boolean | PostgreSQL 연결 여부 |
| uptime_seconds | number | 서버 시작 후 경과 시간 (초) |
| api_status | object | 각 API 상태 ("ok" / "limited" / "no_data" / "no_gemini_key") |

```bash
curl http://localhost:8000/health
```

---

## 2. POST /api/recommend

맛 벡터 또는 저장된 user_id 기반 전통주 추천. 코사인 유사도 + match_reason(추천 이유 2가지) 반환.

`user_vector`와 `user_id` 중 하나 필수. 둘 다 있으면 `user_vector` 우선.

### Request Body — 맛 벡터 직접 입력

```json
{
  "user_vector": {
    "sweetness": 7.5,
    "body": 5.0,
    "carbonation": 3.0,
    "flavor": 6.5,
    "alcohol": 4.0,
    "acidity": 5.0,
    "aroma_intensity": 5.0,
    "finish": 5.0
  },
  "top_k": 5,
  "exclude_ids": []
}
```

### Request Body — user_id로 저장된 프로필 사용

```json
{
  "user_id": "user123",
  "top_k": 5
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| user_vector | object | △ | 사용자 맛 벡터 (각 축 0~10). user_id와 둘 중 하나 필수 |
| user_id | string | △ | survey/convert로 저장한 프로필 ID. user_vector와 둘 중 하나 필수 |
| top_k | number | X | 추천 개수 (기본값: 10, 최대: 50) |
| exclude_ids | array | X | 제외할 전통주 ID 목록 |

### Response

```json
[
  {
    "id": "makgeolli_0",
    "name": "이동 생 쌀 막걸리",
    "similarity": 0.978,
    "similarity_percent": 97.8,
    "abv": 6.0,
    "brewery": "이동양조",
    "region": "경기도",
    "features": "맑고 깨끗한 맛",
    "taste_vector": {
      "sweetness": 7.0,
      "body": 5.0,
      "carbonation": 3.0,
      "flavor": 6.0,
      "alcohol": 4.0,
      "acidity": 5.0,
      "aroma_intensity": 5.0,
      "finish": 5.0
    },
    "match_reason": ["단맛이 잘 맞아요", "풍미가 비슷해요"],
    "is_funding": false,
    "status": "available"
  }
]
```

| 필드 | 타입 | 설명 |
|------|------|------|
| id | string | 전통주 ID |
| name | string | 전통주 이름 |
| similarity | number | 코사인 유사도 (0~1) |
| similarity_percent | number | 유사도 퍼센트 (예: 97.8) |
| abv | number | 알콜 도수 (%) |
| brewery | string/null | 양조장 |
| region | string/null | 지역 |
| features | string/null | 특징 |
| taste_vector | object | 전통주 맛 벡터 |
| match_reason | array | 추천 이유 (가장 유사한 2개 축, 한국어) |
| is_funding | boolean | 펀딩 중인 전통주 여부 |
| status | string | "available" (출시) / "funding" (펀딩 중) |

### 에러 케이스

```json
{ "status": "error", "message": "user_vector 또는 user_id 중 하나는 필수입니다." }
{ "status": "error", "message": "top_k는 1~50 사이여야 합니다." }
```

```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_vector":{"sweetness":7.5,"body":5,"carbonation":3,"flavor":6.5,"alcohol":4,"acidity":5,"aroma_intensity":5,"finish":5},"top_k":5}'
```

---

## 3. POST /api/survey/convert

술BTI 25문항 설문 응답 → 8축 맛 벡터 + BTI 유형 + 취향 요약 변환.

`?user_id=xxx` 쿼리 파라미터를 붙이면 결과가 서버 메모리에 저장되어, 이후 `recommend`나 `taste/profile`에서 user_id만으로 조회 가능.

### Query Parameter

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| user_id | string | X | 저장할 사용자 ID. 제공 시 프로필 저장 |

### Request Body

```json
{
  "q1": 2, "q2": 2, "q3": 2,
  "q4": 6, "q5": 2, "q6": 7, "q7": 5, "q8": 5, "q9": 5,
  "q10": 2, "q11": 2, "q12": 2, "q13": 2, "q14": 7,
  "q15": 3, "q16": 3, "q17": 3, "q18": 5, "q19": 4,
  "q20": 3, "q21": 5, "q22": 5,
  "q23": 1,
  "q24": [1, 4],
  "q25": [1, 2]
}
```

| 문항 | 범위 | 설명 |
|------|------|------|
| q1 | 1~5 | 전통주 경험 수준 (1~2: 입문자, 3: 중급자, 4~5: 전문가) |
| q2 | 1~5 | 선호 도수 (1: 3도↓, 2: 4~6도, 3: 7~9도, 4: 10~13도, 5: 14도↑) |
| q3 | 1~5 | 선호 바디감 (1: 매우 가벼움 ~ 5: 매우 묵직함) |
| q4~q22 | 1~7 | 등간척도 Likert (맛/향/바디감 선호도) |
| q23 | 1~5 | 선호 과일 (1: 감귤류, 2: 베리류, 3: 사과, 4: 포도, 5: 망고) |
| q24 | 배열 | 음식 페어링 (1: 고기, 2: 해산물, 3: 매운음식, 4: 디저트, 5: 치즈) |
| q25 | 배열 | 관심 향 (1: 과일향, 2: 감귤향, 3: 꽃향, 4: 허브향, 5: 쌀향) |

### Response

```json
{
  "status": "success",
  "taste_vector": {
    "sweetness": 8.14,
    "body": 2.64,
    "carbonation": 8.29,
    "flavor": 7.84,
    "alcohol": 3.6,
    "acidity": 7.71,
    "aroma_intensity": 7.21,
    "finish": 4.43
  },
  "bti_code": "SLFU",
  "character_name": "팝핑 과일 에이드",
  "experience_level": "입문자",
  "preferred_abv": "약한 도수(4~6도)",
  "preferred_body": "가벼움",
  "preferred_fruit": "감귤류",
  "preferred_food_pairing": ["고기", "디저트"],
  "preferred_aroma": ["과일향", "감귤향"],
  "taste_profile_summary": "청량하고 달콤하고 산미 있는 취향"
}
```

| 필드 | 설명 |
|------|------|
| taste_vector | 8축 맛 벡터 (각 0~10) |
| bti_code | 4글자 술BTI 코드 (sweetness/body/carbonation/flavor 기준 5.0 이진분류) |
| character_name | BTI 유형 캐릭터명 (16종 중 하나) |
| experience_level | 경험 수준 (입문자 / 중급자 / 전문가) |
| preferred_abv | 선호 도수 (한글) |
| preferred_body | 선호 바디감 (한글) |
| preferred_fruit | 선호 과일 (한글) |
| preferred_food_pairing | 선호 음식 페어링 (한글 리스트) |
| preferred_aroma | 관심 향 (한글 리스트) |
| taste_profile_summary | 맛 벡터 기반 한 줄 취향 요약 |

```bash
# user_id 없이 변환만
curl -X POST "http://localhost:8000/api/survey/convert" \
  -H "Content-Type: application/json" \
  -d '{"q1":2,"q2":2,"q3":2,"q4":6,"q5":2,"q6":7,"q7":5,"q8":5,"q9":5,"q10":2,"q11":2,"q12":2,"q13":2,"q14":7,"q15":3,"q16":3,"q17":3,"q18":5,"q19":4,"q20":3,"q21":5,"q22":5,"q23":1,"q24":[1,4],"q25":[1,2]}'

# user_id 포함 → 프로필 저장
curl -X POST "http://localhost:8000/api/survey/convert?user_id=user123" \
  -H "Content-Type: application/json" \
  -d '{"q1":2,"q2":2,"q3":2,...}'
```

---

## 4. GET /api/taste/profile/{user_id}

`survey/convert?user_id=xxx` 로 저장한 취향 프로필 조회. 서버 재시작 시 초기화됨 (인메모리).

### Path Parameter

| 파라미터 | 설명 |
|----------|------|
| user_id | survey/convert 시 사용한 사용자 ID |

### Response

`survey/convert` 응답과 동일한 구조 반환.

```json
{
  "status": "success",
  "taste_vector": { "sweetness": 8.14, "body": 2.64, "..." : "..." },
  "bti_code": "SLFU",
  "character_name": "팝핑 과일 에이드",
  "experience_level": "입문자",
  "preferred_abv": "약한 도수(4~6도)",
  "preferred_body": "가벼움",
  "preferred_fruit": "감귤류",
  "preferred_food_pairing": ["고기", "디저트"],
  "preferred_aroma": ["과일향", "감귤향"],
  "taste_profile_summary": "청량하고 달콤하고 산미 있는 취향"
}
```

### 에러 케이스
- 404: 해당 user_id로 저장된 프로필 없음 (survey/convert를 먼저 호출해야 함)

```bash
curl http://localhost:8000/api/taste/profile/user123
```

---

## 5. POST /api/taste/update

전통주를 마신 후 취향 평가 입력. 별점 방식과 축별 직접 평가 방식 모두 지원.

### Request Body — 별점 방식 (1~5점)

```json
{
  "user_id": "user123",
  "drink_id": "makgeolli_0",
  "rating": 4,
  "tags": ["달콤", "청량"]
}
```

### Request Body — 축별 직접 평가 방식 (0~10)

```json
{
  "user_id": "user123",
  "drink_id": "makgeolli_0",
  "ratings": {
    "sweetness": 7,
    "body": 5,
    "carbonation": 6,
    "flavor": 7,
    "alcohol": 4,
    "acidity": 5,
    "aroma_intensity": 6,
    "finish": 5
  },
  "tags": []
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| user_id | string | O | 사용자 ID |
| drink_id | string | O | 전통주 ID |
| rating | number | X | 별점 (1~5), `ratings`가 없으면 필수 |
| ratings | object | X | 축별 평가 (0~10), 있으면 `rating`보다 우선 적용 |
| tags | array | X | 자유 태그 |

> `ratings` dict가 있으면 해당 값을 맛 벡터로 직접 사용해 취향을 업데이트합니다.

### Response

```json
{
  "status": "success",
  "message": "사용자 user123의 취향이 업데이트되었습니다."
}
```

```bash
curl -X POST http://localhost:8000/api/taste/update \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","drink_id":"makgeolli_0","ratings":{"sweetness":7,"body":5,"carbonation":6,"flavor":7,"alcohol":4,"acidity":5,"aroma_intensity":6,"finish":5}}'
```

---

## 6. GET /api/taste/history/{user_id}

사용자 취향 히스토리 + 누적된 평가 기반 진화된 맛 벡터 조회.

### Path Parameter

| 파라미터 | 설명 |
|----------|------|
| user_id | 사용자 ID |

### Response

```json
{
  "user_id": "user123",
  "history_count": 3,
  "history": [
    {
      "drink_id": "makgeolli_0",
      "drink_name": "이동 생 쌀 막걸리",
      "rating": null,
      "ratings": {"sweetness": 7, "body": 5, "carbonation": 6, "flavor": 7, "alcohol": 4, "acidity": 5, "aroma_intensity": 6, "finish": 5},
      "tags": [],
      "taste_vector": {"sweetness": 7.0, "body": 5.0, "...": "..."},
      "timestamp": "2026-05-16T00:08:00.000000"
    }
  ],
  "evolved_taste_vector": {
    "sweetness": 5.7,
    "body": 5.0,
    "carbonation": 5.3,
    "flavor": 5.7,
    "alcohol": 4.7,
    "acidity": 5.0,
    "aroma_intensity": 5.3,
    "finish": 5.0
  }
}
```

| 필드 | 설명 |
|------|------|
| history_count | 평가 기록 수 |
| history | 전체 평가 기록 |
| evolved_taste_vector | 평가 누적으로 진화된 사용자 맛 벡터 |

```bash
curl http://localhost:8000/api/taste/history/user123
```

---

## 7. POST /api/chat

전통주 전문 AI 채팅. 막걸리·청주·탁주 등 전통주 관련 질문에만 답변하며, 후속 질문 2개를 추천합니다.

### Request Body

```json
{
  "message": "막걸리와 청주의 차이가 뭔가요?",
  "user_id": "user123",
  "history": [
    {"role": "user", "content": "막걸리에 어울리는 안주가 뭐가 있나요?"},
    {"role": "assistant", "content": "파전, 김치전, 도토리묵 등이 잘 어울립니다."}
  ]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| message | string | O | 사용자 메시지 |
| user_id | string | O | 사용자 ID |
| history | array | X | 이전 대화 기록 (`role` + `content`) |

### Response

```json
{
  "response": "막걸리는 거른 탁주로 쌀·누룩·물로 빚어 걸러낸 술이고, 청주는 발효 후 맑게 걸러낸 술입니다. 막걸리는 뿌옇고 달콤·산미가 있으며, 청주는 맑고 깔끔한 맛이 특징입니다.",
  "context": "traditional_korean_alcohol",
  "suggested_questions": [
    "청주와 막걸리의 차이가 뭔가요?",
    "청주에 어울리는 안주가 있나요?"
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| response | string | AI 답변 |
| context | string | "traditional_korean_alcohol" (관련) / "out_of_scope" (비관련) |
| suggested_questions | array | 키워드 기반 후속 질문 2개 |

> 전통주와 무관한 질문은 Gemini 호출 없이 즉시 거절 (context: "out_of_scope")

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"막걸리 보관 방법이 궁금해요","user_id":"user123","history":[]}'
```

### 에러 케이스
- 503: Gemini 429 quota 초과
- 500: Gemini 연결 오류

---

## 8. POST /api/food/recommend

음식 이름 기반 어울리는 전통주 추천.

### Request Body

```json
{
  "food": "파전",
  "top_k": 3
}
```

### Response

```json
[
  {
    "id": "makgeolli_0",
    "name": "이동 생 쌀 막걸리",
    "abv": 6.0,
    "brewery": "이동양조",
    "region": "경기도",
    "features": "맑고 깨끗한 맛",
    "taste_vector": {"sweetness": 7.0, "...": "..."},
    "reason": "파전와 잘 어울립니다"
  }
]
```

```bash
curl -X POST http://localhost:8000/api/food/recommend \
  -H "Content-Type: application/json" \
  -d '{"food":"파전","top_k":3}'
```

---

## 9. POST /api/recipe/suggest-sub-ingredients

메인재료 + 지역 입력 시 지역 특산물 기반 서브재료 5개 추천 (Gemini 사용).

### Request Body

```json
{
  "main_ingredient": "경기도 쌀",
  "region": "경기도"
}
```

### Response

```json
{
  "sub_ingredients": ["누룩", "유자", "생강", "꿀", "솔잎"]
}
```

```bash
curl -X POST http://localhost:8000/api/recipe/suggest-sub-ingredients \
  -H "Content-Type: application/json" \
  -d '{"main_ingredient":"경기도 쌀","region":"경기도"}'
```

---

## 10. POST /api/recipe/suggest-flavor-tags

레시피 정보 기반 맛 태그 5개 자동 생성 (Gemini 사용).

### Request Body

```json
{
  "title": "경기도 쌀 막걸리",
  "main_ingredient": "경기도 쌀",
  "sub_ingredients": ["누룩", "물"],
  "abv_range": "5~7도"
}
```

### Response

```json
{
  "flavor_tags": ["달콤함", "청량함", "과일향", "깔끔함", "부드러움"]
}
```

```bash
curl -X POST http://localhost:8000/api/recipe/suggest-flavor-tags \
  -H "Content-Type: application/json" \
  -d '{"title":"경기도 쌀 막걸리","main_ingredient":"경기도 쌀","sub_ingredients":["누룩","물"],"abv_range":"5~7도"}'
```

---

## 11. POST /api/recipe/suggest-summary

레시피 정보 기반 프로젝트 요약문 3문장 자동 생성 (Gemini 사용).

### Request Body

```json
{
  "title": "경기도 쌀 막걸리",
  "main_ingredient": "경기도 쌀",
  "sub_ingredients": ["누룩", "물"],
  "abv_range": "5~7도",
  "flavor_tags": ["달콤함", "청량함"],
  "concept": null
}
```

### Response

```json
{
  "summary": "경기도산 쌀을 사용하여 전통 방식으로 양조한 막걸리입니다. 5~7도의 도수로 부드러운 맛과 청량한 산미가 조화를 이룹니다. 달콤하고 깔끔한 맛으로 누구나 즐길 수 있습니다."
}
```

```bash
curl -X POST http://localhost:8000/api/recipe/suggest-summary \
  -H "Content-Type: application/json" \
  -d '{"title":"경기도 쌀 막걸리","main_ingredient":"경기도 쌀","sub_ingredients":["누룩","물"],"abv_range":"5~7도","flavor_tags":["달콤함","청량함"],"concept":null}'
```

---

## 12. POST /api/law/filter

레시피/펀딩 콘텐츠 법률 위반 여부 3단계 자동 검토.

### 검토 단계

1. **키워드 1차 필터** — 명백한 위반 즉시 차단 (미성년자 타겟, 불법 재료 등)
2. **국가법령정보센터 API** — 관련 법령 실시간 조회
3. **Gemini 분석** — 법령 조문 + 콘텐츠 → 위반 여부 판단

### Request Body

```json
{
  "content_type": "recipe",
  "title": "경기도 쌀 막걸리",
  "description": "경기도산 쌀 100% 사용, 전통 누룩으로 양조",
  "ingredients": ["쌀", "누룩", "물"],
  "target_region": "경기도"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| content_type | string | O | "recipe" 또는 "funding" |
| title | string | O | 제목 |
| description | string | O | 설명 |
| ingredients | array | X | 재료 목록 |
| target_region | string | X | 타겟 지역 |

### Response — 정상

```json
{
  "violation": false,
  "details": [],
  "recommendation": "법적 문제가 없습니다."
}
```

### Response — 위반

```json
{
  "violation": true,
  "details": [
    {
      "category": "과대광고/허위표시",
      "law": "식품위생법",
      "reason": "숙취 없다는 표현은 과대광고에 해당합니다",
      "article": "식품위생법 제4조"
    }
  ],
  "recommendation": "'숙취 없는' 표현을 제거하거나 수정해주세요."
}
```

```bash
curl -X POST http://localhost:8000/api/law/filter \
  -H "Content-Type: application/json" \
  -d '{"content_type":"recipe","title":"경기도 쌀 막걸리","description":"경기도산 쌀 100% 사용","ingredients":["쌀","누룩","물"]}'
```

---

## 13. GET /api/law/info

전통주 관련 주요 법령 목록 조회.

### Response

```json
{
  "status": "success",
  "laws": [
    {
      "name": "주세법",
      "law_id": "000123",
      "keywords": ["전통주", "막걸리", "탁주"],
      "description": "주류 제조 및 판매 관련 세법"
    }
  ]
}
```

```bash
curl http://localhost:8000/api/law/info
```

---

## 14. GET /api/insight

양조장용 인사이트 대시보드. 통계 집계 + 예측 + 군집화 + Gemini AI 리포트 제공.

### Query Parameter

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| period | "week" | 분석 기간 ("day" / "week" / "month") |

### Response

```json
{
  "period": "week",
  "summary": "이번 주 막걸리 추천 207회, 평균 선호 도수 6.2도",
  "statistics": {
    "total_recommendations": 207,
    "avg_abv": 6.2,
    "top_regions": ["경기도", "전라도", "충청도"],
    "top_types": ["막걸리", "청주", "탁주"]
  },
  "predictions": {
    "next_week_trend": "단맛 선호 증가 예상",
    "recommended_focus": "저도수 과일 막걸리"
  },
  "clusters": [
    {
      "cluster_id": 0,
      "label": "단맛 선호 그룹",
      "count": 45,
      "avg_vector": {"sweetness": 8.0, "body": 5.0, "...": "..."}
    }
  ],
  "ai_report": "이번 주 주담 플랫폼 분석 결과, 단맛과 청량감을 선호하는 사용자가 전체의 42%를 차지했습니다. 특히 경기도산 생막걸리와 탄산 탁주에 대한 관심이 높았으며, 저도수(5~7도) 제품의 추천 비율이 전주 대비 15% 증가했습니다. 다음 주에는 과일향 막걸리와 스파클링 탁주 중심의 기획을 권장드립니다."
}
```

| 필드 | 설명 |
|------|------|
| period | 분석 기간 |
| summary | 한 줄 요약 |
| statistics | 집계 통계 (추천 수, 평균 도수, 인기 지역/유형) |
| predictions | 다음 기간 트렌드 예측 |
| clusters | 사용자 군집 분석 |
| ai_report | Gemini가 생성한 양조장용 자연어 인사이트 리포트 |

```bash
curl "http://localhost:8000/api/insight?period=week"
```

---

## 15. POST /api/rag/search

전통주 전문 문서 기반 RAG 검색.

### Request Body

```json
{
  "query": "막걸리 발효 온도",
  "top_k": 5,
  "category": null
}
```

### Response

```json
{
  "query": "막걸리 발효 온도",
  "results": [
    {
      "id": "doc_001",
      "title": "막걸리 양조 기초",
      "content": "막걸리 발효에 최적 온도는 15~20도입니다...",
      "score": 0.87
    }
  ],
  "total": 1
}
```

```bash
curl -X POST http://localhost:8000/api/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query":"막걸리 발효 온도","top_k":3}'
```

---

## 16. POST /api/crawler/check

koreansool.co.kr에서 신규 전통주를 감지하고, 새로운 항목이 있으면 auto_pipeline으로 맛 벡터를 자동 생성합니다. 중복 방지를 위해 이미 처리된 항목은 캐시(`data/crawler_seen.json`)에 저장됩니다.

### Response

```json
{
  "status": "ok",
  "checked_at": "2026-05-16T00:10:00.000000",
  "new_count": 2,
  "new_items": [
    {"name": "신규 막걸리A", "crawler_id": "a1b2c3d4e5f6"},
    {"name": "신규 막걸리B", "crawler_id": "b2c3d4e5f6a1"}
  ],
  "total_seen": 52
}
```

| 필드 | 설명 |
|------|------|
| new_count | 이번 크롤링에서 새로 발견된 항목 수 |
| new_items | 신규 항목 목록 (이름 + 내부 ID) |
| total_seen | 전체 누적 감지 항목 수 |

```bash
curl -X POST http://localhost:8000/api/crawler/check
```

---

## 17. POST /api/drinks/request

사용자가 플랫폼에 없는 전통주 등록을 요청합니다. 메모리 기반 저장.

### Request Body

```json
{
  "user_id": "user123",
  "name": "우리동네 막걸리",
  "brewery": "한국양조장",
  "region": "경기도",
  "description": "경기도 연천 쌀로 만든 지역 막걸리"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| user_id | string | O | 요청자 ID |
| name | string | O | 전통주 이름 |
| brewery | string | X | 양조장 |
| region | string | X | 지역 |
| description | string | X | 설명 |

### Response

```json
{
  "status": "success",
  "message": "등록 요청이 접수되었습니다.",
  "request_id": 1
}
```

```bash
curl -X POST http://localhost:8000/api/drinks/request \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","name":"우리동네 막걸리","brewery":"한국양조장","region":"경기도"}'
```

---

## 18. GET /api/drinks/requests

전통주 등록 요청 목록 조회 (관리자용).

### Query Parameter

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| status | (없음, 전체) | "pending" / "approved" / "all" |

### Response

```json
{
  "status": "success",
  "total": 2,
  "requests": [
    {
      "id": 1,
      "user_id": "user123",
      "name": "우리동네 막걸리",
      "brewery": "한국양조장",
      "region": "경기도",
      "description": "경기도 연천 쌀로 만든 지역 막걸리",
      "status": "pending",
      "requested_at": "2026-05-16T00:08:00.000000",
      "approved_at": null,
      "taste_vector": null
    }
  ]
}
```

```bash
curl "http://localhost:8000/api/drinks/requests?status=pending"
```

---

## 19. POST /api/drinks/requests/{id}/approve

등록 요청을 승인하고 auto_pipeline으로 맛 벡터를 자동 생성합니다.

### Path Parameter

| 파라미터 | 설명 |
|----------|------|
| id | 요청 ID (정수) |

### Response

```json
{
  "status": "success",
  "message": "승인 완료. 맛 벡터가 생성되었습니다.",
  "request": {
    "id": 1,
    "name": "우리동네 막걸리",
    "status": "approved",
    "approved_at": "2026-05-16T00:15:00.000000",
    "taste_vector": {
      "sweetness": 6.5,
      "body": 5.0,
      "carbonation": 4.0,
      "flavor": 5.5,
      "alcohol": 4.0,
      "acidity": 5.0,
      "aroma_intensity": 4.5,
      "finish": 5.0
    }
  }
}
```

### 에러 케이스
- 404: 요청 ID를 찾을 수 없는 경우
- 500: auto_pipeline 실행 오류

```bash
curl -X POST http://localhost:8000/api/drinks/requests/1/approve
```

---

---

## 20. POST /api/funding/register

양조장이 펀딩 전통주를 등록하고 즉시 추천 풀에 편입합니다.

### Request Body

```json
{
  "funding_id": "funding_001",
  "name": "경기도 이천 쌀 막걸리",
  "brewery": "이천 양조장",
  "region": "경기도 이천",
  "description": "이천 쌀로 만든 달콤한 막걸리",
  "abv": 6.0,
  "main_ingredient": "이천 쌀",
  "taste_input": {
    "sweetness": 8, "body": 4, "carbonation": 7, "flavor": 6,
    "alcohol": 4, "acidity": 5, "aroma_intensity": 6, "finish": 5
  },
  "brewery_user_id": "brewery_001"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| funding_id | string | O | 펀딩 고유 ID (중복 불가) |
| name | string | O | 전통주 이름 |
| brewery | string | X | 양조장 |
| region | string | X | 지역 |
| description | string | X | 설명 |
| abv | number | X | 도수 (0 초과 100 이하) |
| main_ingredient | string | X | 메인 재료 |
| taste_input | object | X | 맛지표 직접 입력 (없으면 Gemini 자동 생성) |
| brewery_user_id | string | X | 양조장 사용자 ID |

### Response

```json
{
  "status": "success",
  "funding_id": "funding_001",
  "name": "경기도 이천 쌀 막걸리",
  "taste_vector": { "sweetness": 8.0, "body": 4.0, "..." : 0.0 },
  "source": "direct_input",
  "message": "펀딩 전통주가 추천 풀에 편입되었습니다."
}
```

| source 값 | 설명 |
|-----------|------|
| direct_input | taste_input 직접 입력 사용 |
| gemini_auto | Gemini가 자동 생성 |

### 에러 케이스

```json
{ "status": "error", "message": "이미 등록된 펀딩 ID입니다." }
{ "status": "error", "message": "도수는 0~100 사이여야 합니다." }
```

---

## 21. GET /api/funding/{funding_id}

등록된 펀딩 전통주 정보와 맛벡터를 조회합니다.

### Path Parameter

| 파라미터 | 설명 |
|----------|------|
| funding_id | 등록 시 사용한 펀딩 ID |

### Response

```json
{
  "funding_id": "funding_001",
  "name": "경기도 이천 쌀 막걸리",
  "brewery": "이천 양조장",
  "region": "경기도 이천",
  "description": "이천 쌀로 만든 달콤한 막걸리",
  "abv": 6.0,
  "main_ingredient": "이천 쌀",
  "brewery_user_id": "brewery_001",
  "taste_vector": { "sweetness": 8.0, "body": 4.0, "..." : 0.0 },
  "registered_at": "2026-05-22T10:00:00.000000"
}
```

### 에러 케이스
- 404: 해당 funding_id 없음

---

## 22. POST /api/funding/{funding_id}/taste-update

샘플 시음 후 맛벡터를 보정하고 추천 풀에 즉시 반영합니다.

### Request Body

```json
{
  "taste_input": {
    "sweetness": 9, "body": 5, "carbonation": 6, "flavor": 7,
    "alcohol": 4, "acidity": 4, "aroma_intensity": 7, "finish": 6
  }
}
```

### Response

```json
{
  "status": "success",
  "funding_id": "funding_001",
  "taste_vector": { "sweetness": 9.0, "body": 5.0, "..." : 0.0 },
  "message": "맛벡터가 보정되어 추천 풀에 반영되었습니다."
}
```

### 에러 케이스
- 404: 해당 funding_id 없음

---

## 23. POST /api/recipe/register

사용자 레시피를 등록하고 추천 풀에 편입합니다. `taste_input` 없이 `GEMINI_AVAILABLE=false`이면 503 반환.

### Request Body

```json
{
  "recipe_id": "recipe_001",
  "title": "이천 쌀 막걸리",
  "user_id": "user_001",
  "main_ingredient": "이천 쌀",
  "sub_ingredients": ["가평 잣"],
  "abv_range": "6~8도",
  "flavor_tags": ["달콤한", "고소한"],
  "description": "구수하고 달콤한 막걸리",
  "taste_input": null
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| recipe_id | string | O | 레시피 고유 ID |
| title | string | O | 레시피 제목 |
| user_id | string | O | 작성자 ID |
| main_ingredient | string | O | 메인 재료 |
| sub_ingredients | array | X | 서브 재료 |
| abv_range | string | O | 목표 도수 범위 |
| flavor_tags | array | X | 맛 태그 |
| description | string | X | 추가 설명 |
| taste_input | object | X | 맛벡터 직접 입력 (없으면 Gemini 자동 생성) |

### Response

```json
{
  "status": "success",
  "recipe_id": "recipe_001",
  "title": "이천 쌀 막걸리",
  "taste_vector": { "sweetness": 7.0, "body": 5.0, "..." : 0.0 },
  "source": "direct_input",
  "message": "레시피가 추천 풀에 편입되었습니다."
}
```

### 에러 케이스

```json
{ "status": "error", "message": "AI 서비스 점검 중입니다. taste_input을 직접 입력해주세요." }
```

---

## 24. POST /api/recipe/validate

전통주 양조 전문가 AI(Gemini)가 레시피 제작 가능성을 검토합니다. 동일 입력 조합은 60분 캐시.

### Request Body

```json
{
  "title": "이천 쌀 막걸리",
  "main_ingredient": "이천 쌀",
  "sub_ingredients": ["가평 잣", "여주 고구마"],
  "abv_range": "6~8도",
  "flavor_tags": ["달콤한", "고소한"],
  "description": "구수하고 달콤한 막걸리"
}
```

### Response

```json
{
  "feasibility": "high",
  "score": 90,
  "issues": [],
  "suggestions": [
    "고구마 사용량 조절로 단맛 미세 조정 권장",
    "잣 볶는 과정으로 더 깊은 고소함 표현 가능"
  ],
  "summary": "재료 조합이 적절하며 도수 실현 가능성이 높습니다.",
  "cached": false
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| feasibility | string | "high" / "medium" / "low" |
| score | number | 제작 가능성 점수 (0~100) |
| issues | array | 문제점 목록 |
| suggestions | array | 개선안 목록 |
| summary | string | 한 줄 검토 결과 |
| cached | boolean | 캐시 응답 여부 |

### 에러 케이스
- 503: `GEMINI_AVAILABLE=false` 또는 Gemini 429 초과

---

## auto_pipeline 도수 직접 매핑

`auto_pipeline.py`에서 사용하는 알콜 도수 → 점수 변환표.

| 도수 (ABV) | 점수 (0~10) |
|------------|-------------|
| 3도 이하 | 2.0 |
| 4~6도 | 4.0 |
| 7~9도 | 6.0 |
| 10~13도 | 7.5 |
| 14~17도 | 8.5 |
| 18도 이상 | 10.0 |

---

## 환경변수

```bash
GEMINI_API_KEY=발급받은_Gemini_API_키
LAW_API_KEY=국가법령정보센터_API_키
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/juddam
REDIS_URL=redis://localhost:6379
```

| 키 | 발급처 |
|----|--------|
| GEMINI_API_KEY | https://makersuite.google.com/app/apikey |
| LAW_API_KEY | https://www.law.go.kr/LSM/mainInfo.do |

---

## 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload --port 8000

# Swagger UI
open http://localhost:8000/docs
```

## 빠른 테스트

```bash
# 헬스체크
curl http://localhost:8000/health

# 설문 → 맛 벡터 + BTI 유형 + 취향 요약 (프로필 저장 포함)
curl -X POST "http://localhost:8000/api/survey/convert?user_id=user123" \
  -H "Content-Type: application/json" \
  -d '{"q1":2,"q2":2,"q3":2,"q4":6,"q5":2,"q6":7,"q7":5,"q8":5,"q9":5,"q10":2,"q11":2,"q12":2,"q13":2,"q14":7,"q15":3,"q16":3,"q17":3,"q18":5,"q19":4,"q20":3,"q21":5,"q22":5,"q23":1,"q24":[1,4],"q25":[1,2]}'

# 저장된 프로필 조회
curl http://localhost:8000/api/taste/profile/user123

# 추천 — user_id로 (survey/convert 후 사용 가능)
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","top_k":3}'

# 추천 — 맛 벡터 직접 입력
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_vector":{"sweetness":7,"body":5,"carbonation":3,"flavor":6,"alcohol":4,"acidity":5,"aroma_intensity":5,"finish":5},"top_k":3}'

# 채팅
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"막걸리 추천해줘","user_id":"test","history":[]}'

# 법률 필터링
curl -X POST http://localhost:8000/api/law/filter \
  -H "Content-Type: application/json" \
  -d '{"content_type":"recipe","title":"경기도 쌀 막걸리","description":"경기도산 쌀 100% 사용","ingredients":["쌀","누룩","물"]}'

# 크롤러 체크
curl -X POST http://localhost:8000/api/crawler/check
```
