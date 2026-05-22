# 주담 AI 서버 — API 가이드

**Base URL** `http://localhost:8000`  
**Version** `0.3.0`  
**Content-Type** `application/json`

---

## 목차

| # | 메서드 | 경로 | 설명 | Gemini |
|---|--------|------|------|--------|
| 1 | GET | `/` | 서버 상태 확인 | |
| 2 | GET | `/health` | 헬스체크 (기능별 상태) | |
| 3 | POST | `/api/recommend` | 맛벡터 기반 전통주 추천 | |
| 4 | POST | `/api/taste/update` | 사용자 취향 업데이트 | |
| 5 | GET | `/api/taste/history/{user_id}` | 취향 히스토리 조회 | |
| 6 | POST | `/api/food/recommend` | 음식 기반 추천 | |
| 7 | POST | `/api/survey/convert` | 술BTI 설문 → 맛벡터 변환 | |
| 8 | GET | `/api/taste/profile/{user_id}` | 사용자 취향 프로필 조회 | |
| 9 | POST | `/api/recipe/suggest-sub-ingredients` | 서브재료 추천 | ✓ |
| 10 | POST | `/api/recipe/suggest-flavor-tags` | 맛 태그 추천 | ✓ |
| 11 | POST | `/api/recipe/suggest-summary` | 레시피 요약문 생성 | ✓ |
| 12 | POST | `/api/recipe/validate` | 레시피 제작 가능성 검토 | ✓ |
| 13 | POST | `/api/recipe/register` | 레시피 등록 → 추천 풀 편입 | 선택 |
| 14 | POST | `/api/law/filter` | 콘텐츠 법률 필터링 | ✓ |
| 15 | GET | `/api/law/info` | 전통주 관련 법령 목록 | |
| 16 | GET | `/api/insight` | 인사이트 대시보드 | |
| 17 | POST | `/api/rag/search` | 문서 RAG 검색 | |
| 18 | POST | `/api/chat` | 전통주 챗봇 | ✓ |
| 19 | POST | `/api/crawler/check` | 외부 술 정보 크롤링 | |
| 20 | POST | `/api/drinks/request` | 신규 전통주 등록 요청 | |
| 21 | GET | `/api/drinks/requests` | 등록 요청 목록 조회 | |
| 22 | POST | `/api/drinks/requests/{request_id}/approve` | 등록 요청 승인 | |
| 23 | POST | `/api/funding/register` | 펀딩 전통주 등록 | 선택 |
| 24 | GET | `/api/funding/{funding_id}` | 펀딩 정보 조회 | |
| 25 | POST | `/api/funding/{funding_id}/taste-update` | 시음 후 맛벡터 보정 | |
| 26 | POST | `/api/image/generate` | 전통주 이미지 생성 | ✓ |

---

## 공통 사항

### 술BTI 코드 구조 (5글자)

`[단맛 S/D][바디 H/L][탄산 F/M][풍미 C/U][도수 H/L]`

| 축 | H | L |
|----|---|---|
| 단맛 (S/D) | Sweet ≥ 5 | Dry < 5 |
| 바디 (H/L) | Heavy ≥ 5 | Light < 5 |
| 탄산 (F/M) | Fizzy ≥ 5 | Mellow < 5 |
| 풍미 (C/U) | Unique ≥ 5 | Classic < 5 |
| **도수 (H/L)** | **고도수(7도↑) ≥ 5** | **저도수(6도↓) < 5** |

| 코드 | 캐릭터명 |
|------|---------|
| SHFCH | 꿀단지에 빠진 인절미 (고도수) |
| SHFCL | 꿀단지에 빠진 인절미 (저도수) |
| SHFUH | 탄산 톡톡 딸기 요거트 (고도수) |
| SHFUL | 탄산 톡톡 딸기 요거트 (저도수) |
| SHMCH | 쫀득쫀득 꿀 찹쌀떡 (고도수) |
| SHMCL | 쫀득쫀득 꿀 찹쌀떡 (저도수) |
| SHMUH | 포근포근 꽃복숭아 (고도수) |
| SHMUL | 포근포근 꽃복숭아 (저도수) |
| SLFCH | 청량함 가득 사과 푸딩 (고도수) |
| SLFCL | 청량함 가득 사과 푸딩 (저도수) |
| SLFUH | 팝핑 과일 에이드 (고도수) |
| SLFUL | 팝핑 과일 에이드 (저도수) |
| SLMCH | 햇살 머금은 식혜 (고도수) |
| SLMCL | 햇살 머금은 식혜 (저도수) |
| SLMUH | 산들바람 머금은 화전 (고도수) |
| SLMUL | 산들바람 머금은 화전 (저도수) |
| DHFCH | 바삭하게 터지는 현미 누룽지 (고도수) |
| DHFCL | 바삭하게 터지는 현미 누룽지 (저도수) |
| DHFUH | 반전매력 고추냉이 (고도수) |
| DHFUL | 반전매력 고추냉이 (저도수) |
| DHMCH | 묵묵한 바위 속 숭늉 (고도수) |
| DHMCL | 묵묵한 바위 속 숭늉 (저도수) |
| DHMUH | 안개 낀 숲속의 황금사과 (고도수) |
| DHMUL | 안개 낀 숲속의 황금사과 (저도수) |
| DLFCH | 청량한 대나무 숲의 차 (고도수) |
| DLFCL | 청량한 대나무 숲의 차 (저도수) |
| DLFUH | 차가운 도시의 샹그리아 (고도수) |
| DLFUL | 차가운 도시의 샹그리아 (저도수) |
| DLMCH | 대숲에 앉은 맑은 백설기 (고도수) |
| DLMCL | 대숲에 앉은 맑은 백설기 (저도수) |
| DLMUH | 빗소리 들리는 다실의 꽃차 (고도수) |
| DLMUL | 빗소리 들리는 다실의 꽃차 (저도수) |

---

### 맛벡터 구조 (TasteVector)
모든 값은 `0.0 ~ 10.0` 범위의 float.

```json
{
  "sweetness": 5.0,
  "body": 5.0,
  "carbonation": 3.0,
  "flavor": 6.0,
  "alcohol": 4.0,
  "acidity": 4.0,
  "aroma_intensity": 5.0,
  "finish": 5.0
}
```

### 에러 응답 형식
```json
{ "status": "error", "message": "사람이 읽을 수 있는 오류 설명" }
```

| HTTP 코드 | 의미 |
|-----------|------|
| 400 | 요청 파라미터 오류 |
| 404 | 리소스 없음 |
| 422 | Pydantic 유효성 검사 실패 |
| 503 | Gemini AI 서비스 점검 중 |
| 500 | 서버 내부 오류 |

---

## 1. GET `/`

서버 버전 및 엔드포인트 맵 반환.

```bash
curl http://localhost:8000/
```

**응답**
```json
{
  "message": "주담 AI 서버 정상 동작",
  "version": "0.3.0",
  "endpoints": { "recommend": "/api/recommend", "...": "..." }
}
```

---

## 2. GET `/health`

기능별 상태와 서버 운영 현황 반환.

```bash
curl http://localhost:8000/health
```

**응답**
```json
{
  "status": "ok",
  "version": "0.3.0",
  "data_count": 100,
  "funding_count": 3,
  "recipe_count": 5,
  "user_count": 12,
  "gemini_key_loaded": true,
  "gemini_available": true,
  "law_key_loaded": true,
  "db_connected": true,
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

`gemini_available: false`일 때 `recipe / law / chat` → `"limited"`.

---

## 3. POST `/api/recommend`

맛벡터 또는 저장된 user_id 기반으로 전통주 추천.  
`user_vector` 또는 `user_id` 중 하나 필수.

**요청**
```json
{
  "user_id": "user_001",
  "user_vector": {
    "sweetness": 6, "body": 5, "carbonation": 3,
    "flavor": 7, "alcohol": 4, "acidity": 5,
    "aroma_intensity": 6, "finish": 5
  },
  "top_k": 5
}
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| user_id | string | 조건부 | — | 저장된 프로필로 추천 |
| user_vector | TasteVector | 조건부 | — | 직접 맛벡터 입력 |
| top_k | int | N | 5 | 추천 개수 (1~50) |

**응답** (배열)
```json
[
  {
    "id": "makgeolli_001",
    "name": "복순도가 손막걸리",
    "abv": 6.5,
    "brewery": "복순도가",
    "region": "경북 울진",
    "features": "쌀, 찹쌀, 송화",
    "taste_vector": { "sweetness": 6.0, "body": 5.0, "...": 0 },
    "similarity": 0.94,
    "similarity_percent": 94.0,
    "is_funding": false,
    "status": "available"
  }
]
```

**에러**
- 400: `user_vector`와 `user_id` 모두 없을 때
- 400: `top_k`가 1~50 범위 밖일 때

---

## 4. POST `/api/taste/update`

사용자가 전통주를 마신 후 별점 또는 축별 수치로 취향 업데이트.  
`rating` 또는 `ratings` 중 하나 필수.

**요청**
```json
{
  "user_id": "user_001",
  "drink_id": "makgeolli_001",
  "rating": 4.5,
  "tags": ["달콤한", "청량한"],
  "ratings": {
    "sweetness": 7, "body": 4, "carbonation": 5,
    "flavor": 8, "alcohol": 3, "acidity": 4,
    "aroma_intensity": 6, "finish": 6
  }
}
```

**응답**
```json
{ "status": "success", "message": "사용자 user_001의 취향이 업데이트되었습니다." }
```

---

## 5. GET `/api/taste/history/{user_id}`

사용자의 취향 히스토리와 진화된 맛벡터 반환.

```bash
curl http://localhost:8000/api/taste/history/user_001
```

**응답**
```json
{
  "user_id": "user_001",
  "history_count": 3,
  "history": [{ "drink_id": "makgeolli_001", "rating": 4.5 }],
  "evolved_taste_vector": { "sweetness": 6.2, "body": 5.1, "...": 0 }
}
```

---

## 6. POST `/api/food/recommend`

먹고 싶은 음식을 입력하면 어울리는 전통주 추천.

**요청**
```json
{ "food": "삼겹살", "top_k": 5 }
```

**응답** (배열)
```json
[
  {
    "id": "makgeolli_002",
    "name": "장수 막걸리",
    "abv": 6.0,
    "brewery": "서울장수",
    "region": "서울",
    "features": "쌀, 누룩",
    "taste_vector": { "sweetness": 4.0, "...": 0 },
    "reason": "삼겹살의 기름진 맛을 산미로 잡아주는 균형 잡힌 막걸리입니다."
  }
]
```

**에러**
- 400: 음식 이름이 빈 문자열일 때

---

## 7. POST `/api/survey/convert`

술BTI 설문 응답을 맛벡터와 BTI 유형으로 변환.  
`user_id` 쿼리 파라미터 제공 시 프로필 자동 저장.

**요청 필드**

| 필드 | 척도 | 범위 | 설명 |
|------|------|------|------|
| q1 | 서열 | 1~5 | 전통주 경험 수준 |
| q2 | 서열 | 1~5 | 선호 도수 수준 |
| q3 | 서열 | 1~5 | 선호 바디감/색상 수준 |
| q4~q22 | Likert | 1~7 | 단맛·신맛·청량감 등 선호도 |
| q23 | 명목 | 1~5 | 선호 과일 (1감귤/2베리/3사과/4포도/5망고) |
| q24 | 복수선택 | 1~5 | 음식 페어링 (1고기/2해산물/3매운음식/4디저트/5치즈) |
| q25 | 복수선택 | 1~5 | 관심 향 (1과일향/2감귤향/3꽃향/4허브향/5쌀향) |

```bash
curl -X POST "http://localhost:8000/api/survey/convert?user_id=user_001" \
  -H "Content-Type: application/json" \
  -d '{
    "q1":3,"q2":3,"q3":3,
    "q4":6,"q5":2,"q6":5,"q7":6,"q8":5,"q9":5,
    "q10":5,"q11":5,"q12":4,"q13":4,
    "q14":6,"q15":3,"q16":4,"q17":3,"q18":6,"q19":4,"q20":3,"q21":4,"q22":5,
    "q23":3,"q24":[1,4],"q25":[1,3]
  }'
```

**응답**
```json
{
  "status": "success",
  "taste_vector": {
    "sweetness": 6.21, "body": 5.12, "carbonation": 5.48,
    "flavor": 5.83, "alcohol": 4.71, "acidity": 4.52,
    "aroma_intensity": 5.24, "finish": 5.71
  },
  "bti_code": "SHFCL",
  "character_name": "꿀단지에 빠진 인절미 (저도수)",
  "alcohol_label": "저도수(6도 이하)",
  "experience_level": "중급자",
  "preferred_abv": "중간 도수(7~9도)",
  "preferred_body": "보통",
  "preferred_fruit": "사과",
  "preferred_food_pairing": ["고기", "디저트"],
  "preferred_aroma": ["과일향", "꽃향"],
  "taste_profile_summary": "달콤하고 청량한 취향"
}
```

> `bti_code`는 5글자 코드. 마지막 `H`/`L`은 도수 선호 (H=고도수, L=저도수).

---

## 8. GET `/api/taste/profile/{user_id}`

저장된 사용자 취향 프로필 조회 (메모리 → DB 순서로 검색).

```bash
curl http://localhost:8000/api/taste/profile/user_001
```

**응답**: `/api/survey/convert` 응답과 동일한 구조.

**에러**
- 404: 프로필 없음 (`survey/convert`를 먼저 호출 필요)

---

## 9. POST `/api/recipe/suggest-sub-ingredients` ✦ Gemini

메인재료와 지역을 입력하면 지역 특산물 기반 서브재료 5개 추천.

**요청**
```json
{ "main_ingredient": "쌀", "region": "경기도" }
```

**응답**
```json
{
  "sub_ingredients": ["이천 쌀", "여주 고구마", "안성 배", "광주 복숭아", "연천 율무"]
}
```

---

## 10. POST `/api/recipe/suggest-flavor-tags` ✦ Gemini

레시피 정보를 기반으로 맛 태그 5개 이내 추천.

**요청**
```json
{
  "title": "봄날 딸기 막걸리",
  "main_ingredient": "쌀",
  "sub_ingredients": ["논산 딸기", "꿀"],
  "abv_range": "5-7%"
}
```

**응답**
```json
{ "flavor_tags": ["달콤한", "새콤한", "과일향", "청량한", "부드러운"] }
```

---

## 11. POST `/api/recipe/suggest-summary` ✦ Gemini

레시피/펀딩 프로젝트의 3문장 요약문 자동 생성.

**요청**
```json
{
  "title": "봄날 딸기 막걸리",
  "main_ingredient": "쌀",
  "sub_ingredients": ["논산 딸기"],
  "abv_range": "5-7%",
  "flavor_tags": ["달콤한", "새콤한"],
  "concept": "봄의 설레임을 담은 막걸리"
}
```

**응답**
```json
{ "summary": "논산 딸기의 새콤달콤함을 그대로 담은 봄날 한정 막걸리입니다. ..." }
```

---

## 12. POST `/api/recipe/validate` ✦ Gemini

Gemini 양조 전문가가 레시피 제작 가능성을 분석하고 점수화.  
동일 입력은 1시간 캐시 적용.

**요청**
```json
{
  "title": "제주 감귤 막걸리",
  "main_ingredient": "쌀",
  "sub_ingredients": ["제주 감귤", "유기농 설탕"],
  "abv_range": "6-8%",
  "flavor_tags": ["새콤달콤", "청량한"],
  "description": "제주 감귤로 만든 상큼한 막걸리"
}
```

**응답**
```json
{
  "feasibility": "high",
  "score": 85,
  "issues": [],
  "suggestions": ["감귤 껍질 일부 사용 시 향이 더 풍부해집니다"],
  "summary": "산미와 감귤향의 조합이 자연스러운 고품질 막걸리 레시피입니다.",
  "cached": false
}
```

| feasibility | 의미 |
|-------------|------|
| `high` | 제작 가능성 높음 (score ≥ 70) |
| `medium` | 일부 조정 필요 (score 40~69) |
| `low` | 재료/도수 재검토 필요 (score < 40) |

---

## 13. POST `/api/recipe/register`

레시피를 등록하고 추천 풀에 자동 편입.  
`taste_input` 미입력 시 Gemini가 자동으로 맛벡터 생성 (`GEMINI_AVAILABLE: true` 필요).

**요청**
```json
{
  "recipe_id": "recipe_001",
  "user_id": "user_001",
  "title": "봄날 딸기 막걸리",
  "main_ingredient": "쌀",
  "sub_ingredients": ["논산 딸기", "꿀"],
  "abv_range": "5-7%",
  "flavor_tags": ["달콤한", "새콤한"],
  "description": "봄의 설레임을 담은 딸기 막걸리",
  "taste_input": {
    "sweetness": 7, "body": 4, "carbonation": 4,
    "flavor": 8, "alcohol": 3, "acidity": 6,
    "aroma_intensity": 7, "finish": 5
  }
}
```

**응답**
```json
{
  "status": "success",
  "recipe_id": "recipe_001",
  "title": "봄날 딸기 막걸리",
  "taste_vector": { "sweetness": 7.0, "body": 4.0, "...": 0 },
  "source": "direct_input",
  "message": "레시피가 추천 풀에 편입되었습니다."
}
```

`source`: `"direct_input"` | `"gemini_auto"`

---

## 14. POST `/api/law/filter` ✦ Gemini

콘텐츠(펀딩 설명, 레시피 소개)의 주류광고 법률 위반 여부 검토.  
동일 입력은 1시간 캐시 적용.

**요청**
```json
{
  "content_type": "product_description",
  "title": "숙취 해소 막걸리",
  "description": "이 막걸리는 숙취 해소에 효능이 있습니다",
  "ingredients": ["쌀", "누룩"]
}
```

| content_type | 설명 |
|--------------|------|
| `product_description` | 제품 소개 / 펀딩 설명 |
| `recipe` | 레시피 페이지 |

**응답**
```json
{
  "violation": true,
  "details": [
    {
      "category": "건강기능식품 효능 주장",
      "law": "식품위생법 제4조",
      "reason": "'숙취 해소 효능'은 허가받지 않은 의약품적 효능 주장입니다.",
      "article": "제4조 (위해 식품 등의 판매 등 금지)"
    }
  ],
  "recommendation": "효능 표현을 삭제하고 맛과 향으로만 설명해주세요."
}
```

---

## 15. GET `/api/law/info`

서버에 내장된 전통주 관련 법령 목록 조회.

```bash
curl http://localhost:8000/api/law/info
```

**응답**
```json
{
  "status": "success",
  "laws": [
    {
      "name": "주세법",
      "law_id": "LAW001",
      "keywords": ["주류", "제조", "면허"],
      "description": "주류 제조 및 판매에 관한 기본법"
    }
  ]
}
```

---

## 16. GET `/api/insight`

추천 데이터 기반 인사이트 대시보드.

```bash
curl "http://localhost:8000/api/insight?period=week"
```

| 쿼리 파라미터 | 값 | 기본값 |
|---------------|-----|--------|
| period | `day` \| `week` \| `month` | `week` |

**응답** (예시)
```json
{
  "period": "week",
  "top_drinks": [],
  "taste_trends": {},
  "ai_report": "이번 주는 산미 높은 막걸리 선호도가 증가했습니다."
}
```

---

## 17. POST `/api/rag/search`

전통주 관련 문서에서 RAG 기반 검색.

**요청**
```json
{
  "query": "막걸리 발효 온도",
  "top_k": 3,
  "category": "brewing"
}
```

**응답**
```json
{
  "results": [
    {
      "content": "막걸리 발효의 최적 온도는 20~25°C입니다...",
      "source": "전통주 양조 가이드",
      "score": 0.92
    }
  ]
}
```

---

## 18. POST `/api/chat` ✦ Gemini

전통주(막걸리·청주·탁주·약주) 관련 질문에 답변하는 챗봇.  
비관련 질문은 즉시 거절 (Gemini 호출 없음).

**요청**
```json
{
  "message": "막걸리 초보자에게 추천하는 도수는?",
  "user_id": "user_001",
  "history": [
    { "role": "user", "content": "막걸리가 뭔가요?" },
    { "role": "assistant", "content": "막걸리는 쌀을 발효시킨 한국 전통주입니다." }
  ]
}
```

**응답**
```json
{
  "response": "초보자에게는 5~6도 막걸리를 추천드립니다. 부담 없이 즐길 수 있어요.",
  "context": "traditional_korean_alcohol",
  "suggested_questions": [
    "도수별 추천 전통주를 알려주세요",
    "도수 낮은 막걸리를 추천해주세요"
  ]
}
```

비관련 질문 시 `context: "out_of_scope"` 반환.

---

## 19. POST `/api/crawler/check`

외부 쇼핑몰/사이트에서 전통주 정보 크롤링.

**요청**
```json
{ "url": "https://example.com/makgeolli", "drink_name": "복순도가" }
```

**응답**
```json
{
  "status": "success",
  "drink_info": { "name": "복순도가 손막걸리", "abv": 6.5 }
}
```

---

## 20. POST `/api/drinks/request`

DB에 없는 전통주를 관리자 승인 방식으로 등록 요청.

**요청**
```json
{
  "name": "양평 더 쌀 막걸리",
  "brewery": "양평양조장",
  "region": "경기 양평",
  "abv": 6.0,
  "description": "양평 지역 쌀로 빚은 막걸리"
}
```

**응답**
```json
{
  "status": "success",
  "request_id": "req_20260522_001",
  "message": "등록 요청이 접수되었습니다. 검토 후 추가됩니다."
}
```

---

## 21. GET `/api/drinks/requests`

전통주 등록 요청 목록 전체 조회.

```bash
curl http://localhost:8000/api/drinks/requests
```

**응답**
```json
{
  "requests": [
    {
      "request_id": "req_20260522_001",
      "name": "양평 더 쌀 막걸리",
      "status": "pending",
      "created_at": "2026-05-22T10:00:00"
    }
  ]
}
```

---

## 22. POST `/api/drinks/requests/{request_id}/approve`

등록 요청을 승인하고 전통주를 추천 풀에 추가.

```bash
curl -X POST http://localhost:8000/api/drinks/requests/req_20260522_001/approve
```

**응답**
```json
{
  "status": "success",
  "message": "양평 더 쌀 막걸리가 추천 풀에 추가되었습니다."
}
```

---

## 23. POST `/api/funding/register`

펀딩 전통주를 등록하고 추천 풀에 편입 (`is_funding: true`로 마킹).  
`taste_input` 미입력 시 Gemini가 자동으로 맛벡터 생성.

**요청**
```json
{
  "funding_id": "funding_001",
  "name": "한라봉 막걸리",
  "brewery": "제주양조장",
  "brewery_user_id": "brewer_001",
  "region": "제주",
  "abv": 7.0,
  "main_ingredient": "쌀",
  "description": "제주 한라봉을 넣은 상큼한 막걸리",
  "taste_input": {
    "sweetness": 6, "body": 4, "carbonation": 5,
    "flavor": 8, "alcohol": 4, "acidity": 7,
    "aroma_intensity": 7, "finish": 5
  }
}
```

**응답**
```json
{
  "status": "success",
  "funding_id": "funding_001",
  "name": "한라봉 막걸리",
  "taste_vector": { "sweetness": 6.0, "body": 4.0, "...": 0 },
  "source": "direct_input",
  "message": "펀딩 전통주가 추천 풀에 편입되었습니다."
}
```

**에러**
- 400: 이미 등록된 `funding_id`
- 400: `abv`가 0~100 범위 밖

---

## 24. GET `/api/funding/{funding_id}`

등록된 펀딩 전통주의 정보와 맛벡터 조회.

```bash
curl http://localhost:8000/api/funding/funding_001
```

**응답**
```json
{
  "funding_id": "funding_001",
  "name": "한라봉 막걸리",
  "brewery": "제주양조장",
  "region": "제주",
  "description": "제주 한라봉을 넣은 상큼한 막걸리",
  "abv": 7.0,
  "main_ingredient": "쌀",
  "brewery_user_id": "brewer_001",
  "taste_vector": { "sweetness": 6.0, "body": 4.0, "...": 0 },
  "registered_at": "2026-05-22T10:00:00"
}
```

**에러**
- 404: 존재하지 않는 `funding_id`

---

## 25. POST `/api/funding/{funding_id}/taste-update`

샘플 시음 후 맛벡터를 보정하고 추천 풀에 즉시 반영.

**요청**
```json
{
  "taste_input": {
    "sweetness": 7, "body": 4, "carbonation": 5,
    "flavor": 8, "alcohol": 4, "acidity": 6,
    "aroma_intensity": 7, "finish": 5
  }
}
```

**응답**
```json
{
  "status": "success",
  "funding_id": "funding_001",
  "taste_vector": { "sweetness": 7.0, "body": 4.0, "...": 0 },
  "message": "맛벡터가 보정되어 추천 풀에 반영되었습니다."
}
```

**에러**
- 404: 존재하지 않는 `funding_id`

---

## 26. POST `/api/image/generate` ✦ Gemini

전통주 정보를 기반으로 Gemini가 이미지 생성 프롬프트를 작성하고,  
`HUGGINGFACE_TOKEN` 설정 시 Stable Diffusion으로 실제 이미지를 생성.

**요청**
```json
{
  "name": "이천 쌀 막걸리",
  "description": "이천 쌀로 만든 달콤한 막걸리",
  "flavor_tags": ["달콤한", "고소한"],
  "region": "경기도 이천"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| name | string | Y | 전통주 이름 |
| description | string | Y | 전통주 설명 |
| flavor_tags | string[] | N | 맛 태그 목록 |
| region | string | N | 지역 |

**응답 — 이미지 생성 성공**
```json
{
  "status": "success",
  "image_base64": "iVBORw0KGgoAAAANS...",
  "prompt_used": "A beautiful Korean traditional rice wine bottle...",
  "format": "jpeg"
}
```

**응답 — 프롬프트만 생성 (HUGGINGFACE_TOKEN 미설정)**
```json
{
  "status": "prompt_only",
  "prompt_used": "A beautiful Korean traditional rice wine bottle with ceramic cup, bamboo background, soft natural lighting, warm tones, product photography style",
  "message": "HUGGINGFACE_TOKEN 설정 시 이미지 자동 생성 가능합니다."
}
```

**응답 — Gemini 키 없음**
```json
{
  "status": "disabled",
  "message": "이미지 생성 기능이 비활성화되어 있습니다."
}
```

| status | 의미 |
|--------|------|
| `success` | 이미지 생성 완료 (base64 포함) |
| `prompt_only` | Gemini 프롬프트만 생성 (HF 토큰 필요) |
| `disabled` | GEMINI_API_KEY 미설정 |
| `error` | 생성 중 오류 |

**펀딩/레시피 등록 시 자동 이미지 생성**

`/api/funding/register` 또는 `/api/recipe/register` 요청에 `auto_generate_image: true` 추가 시 이미지 생성 결과가 응답에 포함됩니다.

```json
{
  "funding_id": "funding_001",
  "name": "제주 한라봉 막걸리",
  "auto_generate_image": true
}
```

응답에 `"image"` 키 추가:
```json
{
  "status": "success",
  "funding_id": "funding_001",
  "...": "...",
  "image": {
    "status": "prompt_only",
    "prompt_used": "Korean traditional citrus rice wine...",
    "message": "HUGGINGFACE_TOKEN 설정 시 이미지 자동 생성 가능합니다."
  }
}
```

**에러**
- 503: `GEMINI_AVAILABLE: false`일 때

---

## 주요 흐름 요약

### 사용자 추천 흐름
```
POST /api/survey/convert?user_id=XXX   ← 설문 응답
    ↓ taste_vector + bti_code 저장
POST /api/recommend (user_id 만으로 호출 가능)
    ↓ similarity_percent 순 정렬
    ↓ 동일 양조장 최대 2개 제한
    ↓ 펀딩 전통주 최소 1개 보장
추천 결과 반환
```

### 펀딩 등록 흐름
```
POST /api/recipe/suggest-sub-ingredients   ← 지역 특산물 서브재료 추천
POST /api/recipe/suggest-flavor-tags       ← 맛 태그 추천
POST /api/recipe/validate                  ← 제작 가능성 점수 확인
POST /api/law/filter                       ← 광고 문구 법률 검토
    ↓
POST /api/funding/register                 ← 추천 풀 편입 (is_funding=true)
    ↓ 시음 후
POST /api/funding/{id}/taste-update        ← 맛벡터 정밀 보정
```
