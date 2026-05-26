# 주담 AI 서버 — API 가이드

**Base URL** `http://localhost:8000`  
**Version** `0.3.0`  
**Content-Type** `application/json`

---

## 목차

| # | 메서드 | 경로 | 설명 | Gemini |
|---|--------|------|------|--------|
| 1 | GET | `/` | 서버 상태 확인 | |
| 2 | GET | `/health` | 헬스체크 (기능별 상태 + KNN 상태) | |
| 3 | POST | `/api/recommend` | 맛벡터 기반 전통주 추천 (food_pairing 앙상블) | |
| 4 | POST | `/api/taste/update` | 사용자 취향 업데이트 | |
| 5 | GET | `/api/taste/history/{user_id}` | 취향 히스토리 조회 | |
| 6 | POST | `/api/survey/convert` | 술BTI 설문 → 맛벡터 변환 | |
| 7 | POST | `/api/bti/feedback` | BTI 결과 피드백 수집 (KNN 학습 데이터) | |
| 8 | GET | `/api/taste/profile/{user_id}` | 사용자 취향 프로필 조회 | |
| 9 | POST | `/api/recipe/suggest-sub-ingredients` | 서브재료 추천 | ✓ |
| 10 | POST | `/api/recipe/suggest-flavor-tags` | 맛 태그 추천 | ✓ |
| 11 | POST | `/api/recipe/suggest-summary` | 레시피 요약문 생성 | ✓ |
| 12 | POST | `/api/recipe/validate` | 레시피 제작 가능성 검토 | ✓ |
| 13 | POST | `/api/recipe/register` | 레시피 등록 → 추천 풀 편입 | 선택 |
| 14 | POST | `/api/law/filter` | 콘텐츠 법률 필터링 | ✓ |
| 15 | GET | `/api/law/info` | 전통주 관련 법령 목록 | |
| 16 | GET | `/api/insight` | 인사이트 대시보드 | |
| 17 | POST | `/api/chat` | 전통주 챗봇 | ✓ |
| 18 | POST | `/api/chat/stream` | 스트리밍 챗봇 | ✓ |
| 19 | POST | `/api/drinks/request` | 신규 전통주 등록 요청 | |
| 20 | GET | `/api/drinks/requests` | 등록 요청 목록 조회 | |
| 21 | POST | `/api/drinks/requests/{request_id}/approve` | 등록 요청 승인 | |
| 22 | POST | `/api/funding/register` | 펀딩 전통주 등록 | 선택 |
| 23 | GET | `/api/funding/{funding_id}` | 펀딩 정보 조회 | |
| 24 | POST | `/api/funding/{funding_id}/taste-update` | 시음 후 맛벡터 보정 | |
| 25 | POST | `/api/image/generate` | 전통주 이미지 생성 | ✓ |
| 26 | GET | `/api/recipe/ingredient-region` | 메인재료 → 추천 지역 자동 조회 | |
| 27 | POST | `/api/brewery/verify-ocr` | 양조장 인증 서류 OCR (3종) | ✓ |

---

## 공통 사항

### 술BTI 코드 구조 (5글자)

`[단맛 S/D][바디 H/L][탄산 F/M][풍미 U/C][도수 H/L]`

| 축 | 문자 의미 | 조건 |
|----|----------|------|
| 단맛 (S/D) | S = Sweet, D = Dry | sweetness ≥ 5 → S |
| 바디 (H/L) | H = Heavy, L = Light | body ≥ 5 → H |
| 탄산 (F/M) | F = Fizzy, M = Mellow | carbonation ≥ 5 → F |
| 풍미 (U/C) | U = Unique, C = Classic | flavor ≥ 5 → U |
| 도수 (H/L) | H = High, L = Low | alcohol ≥ 9 → H |

> KNN 피드백 데이터가 10개 이상 쌓이면 `scripts/train_knn.py` 실행 후 서버 재시작 시 KNN 분류로 전환됩니다.  
> 현재 분류 방식은 `/api/survey/convert` 응답의 `bti_method` 필드에서 확인 가능합니다.

| 코드 | 캐릭터명 |
|------|---------|
| SHFUH | 탄산 톡톡 딸기 요거트 (고도수) |
| SHFUL | 탄산 톡톡 딸기 요거트 (저도수) |
| SHFCH | 꿀단지에 빠진 인절미 (고도수) |
| SHFCL | 꿀단지에 빠진 인절미 (저도수) |
| SHMUH | 포근포근 꽃복숭아 (고도수) |
| SHMUL | 포근포근 꽃복숭아 (저도수) |
| SHMCH | 쫀득쫀득 꿀 찹쌀떡 (고도수) |
| SHMCL | 쫀득쫀득 꿀 찹쌀떡 (저도수) |
| SLFUH | 팝핑 과일 에이드 (고도수) |
| SLFUL | 팝핑 과일 에이드 (저도수) |
| SLFCH | 청량함 가득 사과 푸딩 (고도수) |
| SLFCL | 청량함 가득 사과 푸딩 (저도수) |
| SLMUH | 산들바람 머금은 화전 (고도수) |
| SLMUL | 산들바람 머금은 화전 (저도수) |
| SLMCH | 햇살 머금은 식혜 (고도수) |
| SLMCL | 햇살 머금은 식혜 (저도수) |
| DHFUH | 반전매력 고추냉이 (고도수) |
| DHFUL | 반전매력 고추냉이 (저도수) |
| DHFCH | 바삭하게 터지는 현미 누룽지 (고도수) |
| DHFCL | 바삭하게 터지는 현미 누룽지 (저도수) |
| DHMUH | 안개 낀 숲속의 황금사과 (고도수) |
| DHMUL | 안개 낀 숲속의 황금사과 (저도수) |
| DHMCH | 묵묵한 바위 속 숭늉 (고도수) |
| DHMCL | 묵묵한 바위 속 숭늉 (저도수) |
| DLFUH | 차가운 도시의 샹그리아 (고도수) |
| DLFUL | 차가운 도시의 샹그리아 (저도수) |
| DLFCH | 청량한 대나무 숲의 차 (고도수) |
| DLFCL | 청량한 대나무 숲의 차 (저도수) |
| DLMUH | 빗소리 들리는 다실의 꽃차 (고도수) |
| DLMUL | 빗소리 들리는 다실의 꽃차 (저도수) |
| DLMCH | 대숲에 앉은 맑은 백설기 (고도수) |
| DLMCL | 대숲에 앉은 맑은 백설기 (저도수) |

---

### 맛벡터 구조 (TasteVector)

모든 값은 `0.0 ~ 10.0` 범위의 float. 설문 변환 또는 직접 입력 모두 동일한 구조.

```json
{
  "sweetness":       5.0,
  "body":            5.0,
  "carbonation":     3.0,
  "flavor":          6.0,
  "alcohol":         4.0,
  "acidity":         4.0,
  "aroma_intensity": 5.0,
  "finish":          5.0
}
```

| 축 | 낮음 (0~4) | 보통 (5) | 높음 (6~10) |
|----|-----------|---------|------------|
| sweetness | 드라이함 | 중간 | 달콤함 |
| body | 가벼운 바디 | 중간 | 묵직한 바디 |
| carbonation | 탄산 없음 | 약탄산 | 강탄산 |
| flavor | 깔끔함 | 중간 | 개성 강한 풍미 |
| alcohol | 저도수 | 중도수 | 고도수 |
| acidity | 산미 없음 | 약산미 | 강산미 |
| aroma_intensity | 향 약함 | 중간 | 향 강함 |
| finish | 여운 짧음 | 중간 | 여운 긺 |

---

### 에러 응답 형식

```json
{ "status": "error", "message": "사람이 읽을 수 있는 오류 설명" }
```

| HTTP 코드 | 의미 |
|-----------|------|
| 400 | 요청 파라미터 오류 |
| 404 | 리소스 없음 |
| 422 | Pydantic 유효성 검사 실패 (필드 타입/범위 오류) |
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
  "endpoints": {
    "recommend": "/api/recommend",
    "survey":    "/api/survey/convert",
    "chat":      "/api/chat",
    "health":    "/health"
  }
}
```

---

## 2. GET `/health`

기능별 상태, KNN 모델 상태, 서버 운영 현황 반환.

```bash
curl http://localhost:8000/health
```

**응답**
```json
{
  "status": "ok",
  "version": "0.3.0",
  "data_count": 207,
  "funding_count": 3,
  "recipe_count": 5,
  "user_count": 12,
  "gemini_key_loaded": true,
  "gemini_available": true,
  "law_key_loaded": true,
  "db_connected": true,
  "knn_model_loaded": false,
  "bti_feedback_count": 42,
  "uptime_seconds": 3600,
  "pool_breakdown": {
    "base":     207,
    "funding":  3,
    "recipe":   5,
    "approved": 0
  },
  "api_status": {
    "recommend": "ok",
    "recipe":    "ok",
    "law":       "ok",
    "chat":      "ok",
    "insight":   "ok"
  }
}
```

| 필드 | 설명 |
|------|------|
| `knn_model_loaded` | `true` = KNN 모델 로드됨, BTI 분류에 KNN 사용 중 |
| `bti_feedback_count` | DB 연결 시 DB 카운트, 미연결 시 `data/bti_feedback.json` 카운트 |
| `gemini_available` | `false`이면 `recipe / law / chat` 상태 → `"limited"` |
| `pool_breakdown` | 각 풀별 전통주 수 (추천 시 `pool` 파라미터와 대응) |

---

## 3. POST `/api/recommend`

맛벡터 또는 저장된 `user_id` 기반으로 전통주 추천.  
`user_vector` 또는 `user_id` 중 **하나 필수**.

**추천 앙상블 가중치**

| 소스 | 가중치 | 설명 |
|------|--------|------|
| taste (코사인 유사도) | 0.65 | 맛벡터 8축 비교 (핵심) |
| ingredient (자카드 유사도) | 0.15 | 원재료 겹치는 정도 |
| region | 0.10 | 같은 지역이면 +0.1 |
| food_pairing | 0.10 | 사용자 음식 선호 ↔ 전통주 features 텍스트 매칭 |

> `food_pairing` 점수는 설문 q24에서 저장된 `preferred_food_pairing` 또는 요청의 `food_pairing` 필드로 계산됩니다.

**요청**
```json
{
  "user_id":     "user_001",
  "top_k":       5,
  "pool":        "all",
  "food_pairing": ["고기", "디저트"],
  "exclude_ids": ["makgeolli_001"]
}
```

또는 맛벡터 직접 입력:
```json
{
  "user_vector": {
    "sweetness": 6, "body": 5, "carbonation": 3,
    "flavor": 7, "alcohol": 4, "acidity": 5,
    "aroma_intensity": 6, "finish": 5
  },
  "top_k": 5,
  "pool":  "all",
  "food_pairing": ["고기", "해산물"]
}
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| user_id | string | 조건부 | — | 저장된 프로필로 추천. `user_vector`와 동시 입력 시 `user_vector` 우선 |
| user_vector | TasteVector | 조건부 | — | 맛벡터 8축 직접 입력 (0.0~10.0) |
| top_k | int | N | 10 | 추천 결과 개수 (1~50) |
| pool | string | N | `"all"` | 추천 대상 풀 선택 |
| food_pairing | string[] | N | null | 음식 선호 한글 리스트. `user_id` 사용 시 프로필의 `preferred_food_pairing`으로 자동 대체. 직접 입력하면 우선 적용 |
| exclude_ids | string[] | N | `[]` | 결과에서 제외할 전통주 ID 목록 |
| weights | object | N | null | 앙상블 가중치 직접 지정 `{"taste":0.65,"ingredient":0.15,"region":0.1,"food":0.1}` |

**food_pairing 선택 가능 값** (설문 q24 레이블과 동일)

| 값 | 설명 |
|----|------|
| `"고기"` | 고기 요리 전반 (갈비, 삼겹살, 불고기 등) |
| `"해산물"` | 홍어, 오징어, 조개, 회 등 |
| `"매운음식"` | 김치찌개, 떡볶이, 청양고추 안주 등 |
| `"디저트"` | 한과, 떡, 달콤한 안주 등 |
| `"치즈"` | 치즈, 크림, 유제품 안주 등 |

**pool 값**

| 값 | 설명 |
|----|------|
| `all` | base + funding + recipe + approved 전체 (기본값). 펀딩 전통주 최소 1개 보장 |
| `base` | JSON/DB 로드 기본 전통주만 (207개) |
| `funding` | `/api/funding/register`로 등록된 펀딩 전통주만 |
| `recipe` | `/api/recipe/register`로 등록된 레시피 전통주만 |
| `approved` | `/api/drinks/requests/{id}/approve` 승인 완료 전통주만 |

**응답** (배열)
```json
[
  {
    "id":                 "makgeolli_042",
    "name":               "복순도가 손막걸리",
    "abv":                6.5,
    "brewery":            "복순도가",
    "region":             "경북 울진",
    "features":           "청아한 산미와 풍부한 과일향이 특징...",
    "taste_vector":       { "sweetness": 6.0, "body": 5.0, "carbonation": 4.0, "flavor": 7.0, "alcohol": 4.0, "acidity": 6.0, "aroma_intensity": 7.0, "finish": 6.0 },
    "similarity":         0.94,
    "similarity_percent": 94.0,
    "match_reason":       ["산미가 비슷해요", "향이 잘 맞아요"],
    "is_funding":         false,
    "status":             "available"
  }
]
```

| 응답 필드 | 설명 |
|----------|------|
| `similarity_percent` | 앙상블 유사도 × 100 (0~100) |
| `match_reason` | 가장 가까운 맛축 상위 2개 한글 설명 |
| `is_funding` | `true` = 펀딩 전통주 |
| `status` | `"available"` \| `"funding"` |

**에러**
- 400: `user_vector`와 `user_id` 모두 없을 때
- 400: `top_k`가 1~50 범위 밖일 때

---

## 4. POST `/api/taste/update`

사용자가 전통주를 시음한 후 별점 또는 축별 수치로 취향 업데이트.  
`rating` 또는 `ratings` 중 **하나 필수**.

**요청**
```json
{
  "user_id":  "user_001",
  "drink_id": "makgeolli_042",
  "rating":   4,
  "tags":     ["달콤한", "청량한"],
  "ratings": {
    "sweetness": 7, "body": 4, "carbonation": 5,
    "flavor": 8, "alcohol": 3, "acidity": 4,
    "aroma_intensity": 6, "finish": 6
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| user_id | string | Y | 사용자 ID (1~50자) |
| drink_id | string | Y | 전통주 ID (추천 응답의 `id` 값) |
| rating | float | 조건부 | 별점 (1~5). `ratings` 없으면 필수 |
| ratings | TasteVector | 조건부 | 축별 직접 평가 (0~10). 있으면 `rating`보다 우선 적용 |
| tags | string[] | N | 자유 태그 (예: `["달콤한", "산미 있는"]`) |

> `ratings`(축별)를 제공하면 더 정밀한 취향 진화 트래킹이 적용됩니다.  
> `rating`(별점)만 제공하면 ★5=+1.0, ★4=+0.5, ★3=0, ★2=-0.5, ★1=-1.0 가중치로 벡터 업데이트.

**응답**
```json
{ "status": "success", "message": "사용자 user_001의 취향이 업데이트되었습니다." }
```

---

## 5. GET `/api/taste/history/{user_id}`

사용자의 시음 히스토리와 히스토리 기반으로 진화된 맛벡터 반환.

```bash
curl http://localhost:8000/api/taste/history/user_001
```

**응답**
```json
{
  "user_id":             "user_001",
  "history_count":       3,
  "history": [
    {
      "drink_id":     "makgeolli_042",
      "drink_name":   "복순도가 손막걸리",
      "rating":       4,
      "tags":         ["달콤한"],
      "taste_vector": { "sweetness": 6.0, "..." : 0 },
      "timestamp":    "2026-05-22T10:00:00"
    }
  ],
  "evolved_taste_vector": { "sweetness": 6.2, "body": 5.1, "carbonation": 3.8, "flavor": 6.5, "alcohol": 4.1, "acidity": 5.3, "aroma_intensity": 6.0, "finish": 5.5 }
}
```

> `evolved_taste_vector`는 시음 이력이 쌓일수록 초기 프로필에서 실제 취향으로 수렴합니다.  
> `/api/recommend`에서 `user_id`로 추천 시 이 진화된 벡터가 자동 사용됩니다.

---

## 6. POST `/api/survey/convert`

술BTI 설문 25문항 응답을 맛벡터·BTI 유형·취향 요약으로 변환.  
`user_id` 쿼리 파라미터 제공 시 프로필을 메모리+DB에 자동 저장.

> **bti_confidence** 필드로 분류 신뢰도를 확인할 수 있습니다.  
> KNN 학습 데이터가 쌓이면 `bti_method`가 `"knn"` 또는 `"hybrid_agree"` 로 전환됩니다.

**URL**
```
POST /api/survey/convert?user_id=user_001
```

**요청 필드 상세**

| 필드 | 척도 | 범위 | 설명 |
|------|------|------|------|
| q1 | 서열 | 1~5 | 전통주 경험 수준 (1=완전 처음, 3=가끔 마심, 5=전문가 수준) |
| q2 | 서열 | 1~5 | 선호 도수 (1=무알코올 선호, 3=중간 도수, 5=고도수 선호) |
| q3 | 서열 | 1~5 | 선호 바디감 (1=맑고 가벼움, 3=중간, 5=진하고 묵직함) |
| q4 | Likert | 1~7 | 단맛 선호도 (1=전혀 안 단 것, 7=매우 달콤한 것) |
| q5 | Likert | 1~7 | 산미 선호도 (1=산미 싫음, 7=강한 산미 좋음) |
| q6 | Likert | 1~7 | 청량감 선호도 (1=탄산 없는 것, 7=강한 탄산) |
| q7 | Likert | 1~7 | 바디감 선호도 (1=가벼운 것, 7=묵직한 것) |
| q8 | Likert | 1~7 | 여운 선호도 (1=깔끔하게 끝남, 7=긴 여운) |
| q9 | Likert | 1~7 | 향 복잡도 선호도 (1=단순한 향, 7=복잡한 향) |
| q10 | Likert | 1~7 | 식감 선호도 (1=물처럼 맑음, 7=걸쭉함) |
| q11 | Likert | 1~7 | 색상 선호도 (1=맑은 투명, 7=불투명 탁함) |
| q12 | Likert | 1~7 | 도수에 대한 민감도 (1=도수 낮을수록 좋음, 7=높을수록 좋음) |
| q13 | Likert | 1~7 | 전통 재료 선호도 (1=현대적 재료, 7=전통 누룩/쌀) |
| q14 | Likert | 1~7 | 탄산감 필요 정도 (1=전혀 불필요, 7=꼭 있어야 함) |
| q15 | Likert | 1~7 | 향 강도 선호도 (1=향 없는 것, 7=향 아주 강한 것) |
| q16 | Likert | 1~7 | 음용 속도 (1=천천히 음미, 7=빠르게 마심) |
| q17 | Likert | 1~7 | 발효 향 선호도 (1=발효 향 싫음, 7=발효 향 좋음) |
| q18 | Likert | 1~7 | 과일/꽃 향 선호도 (1=전혀 불필요, 7=과일·꽃향 필수) |
| q19 | Likert | 1~7 | 드라이함 선호도 (1=달콤함 선호, 7=드라이함 선호) |
| q20 | Likert | 1~7 | 발효 복잡도 선호도 (1=단순 발효, 7=복잡한 발효) |
| q21 | Likert | 1~7 | 알코올 느낌 선호도 (1=알코올 느낌 싫음, 7=알코올 느낌 좋음) |
| q22 | Likert | 1~7 | 오크/숙성 향 선호도 (1=숙성 향 싫음, 7=숙성 향 좋음) |
| q23 | 명목 | 1~5 | 선호 과일 (1=감귤류, 2=베리류, 3=사과, 4=포도, 5=망고) |
| q24 | 복수선택 | 1~5 | 음식 페어링 선호 (1=고기, 2=해산물, 3=매운음식, 4=디저트, 5=치즈). 배열로 복수 선택 가능 |
| q25 | 복수선택 | 1~5 | 관심 향 (1=과일향, 2=감귤향, 3=꽃향, 4=허브향, 5=쌀향). 배열로 복수 선택 가능 |

**요청 예시**
```bash
curl -X POST "http://localhost:8000/api/survey/convert?user_id=user_001" \
  -H "Content-Type: application/json" \
  -d '{
    "q1": 3,  "q2": 3,  "q3": 3,
    "q4": 6,  "q5": 2,  "q6": 5,  "q7": 6,  "q8": 5,  "q9": 5,
    "q10": 5, "q11": 5, "q12": 4, "q13": 4,
    "q14": 6, "q15": 3, "q16": 4, "q17": 3, "q18": 6, "q19": 4,
    "q20": 3, "q21": 4, "q22": 5,
    "q23": 3, "q24": [1, 4], "q25": [1, 3]
  }'
```

**응답**
```json
{
  "status":               "success",
  "taste_vector": {
    "sweetness":       6.21,
    "body":            5.12,
    "carbonation":     5.48,
    "flavor":          5.83,
    "alcohol":         4.71,
    "acidity":         4.52,
    "aroma_intensity": 5.24,
    "finish":          5.71
  },
  "bti_code":             "SHFCL",
  "bti_method":           "rule_based",
  "bti_confidence":       "medium",
  "character_name":       "꿀단지에 빠진 인절미 (저도수)",
  "alcohol_label":        "저도수(8도 이하)",
  "experience_level":     "중급자",
  "preferred_abv":        "중간 도수(7~9도)",
  "preferred_body":       "보통",
  "preferred_fruit":      "사과",
  "preferred_food_pairing": ["고기", "디저트"],
  "preferred_aroma":      ["과일향", "꽃향"],
  "taste_profile_summary": "달콤하고 청량한 취향"
}
```

| 응답 필드 | 설명 |
|----------|------|
| `bti_code` | 5글자 BTI 코드 |
| `bti_method` | `"rule_based"` / `"knn"` / `"hybrid_agree"` / `"rule_based_fallback"` |
| `bti_confidence` | `"high"` (KNN+규칙 일치 또는 KNN확률≥0.7) / `"medium"` (기본) / `"low"` (KNN 신뢰도 낮음) |
| `preferred_food_pairing` | q24 선택 결과 한글 레이블 배열 — `/api/recommend` food_pairing에 자동 연동 |
| `taste_profile_summary` | 맛 프로필 3단어 이내 요약 |

---

## 7. POST `/api/bti/feedback`

BTI 분류 결과에 대한 사용자 피드백 수집.  
`is_correct: true`인 항목이 **KNN 모델 학습 데이터**로 활용됩니다.  
DB 연결 시 DB 저장, 미연결 시 `data/bti_feedback.json` fallback.

**요청**
```json
{
  "user_id":            "user_001",
  "bti_code":           "SHFCL",
  "is_correct":         true,
  "actual_preference":  null
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| user_id | string | Y | 사용자 ID (1~50자). 해당 사용자의 `taste_vector`가 함께 저장됨 |
| bti_code | string | Y | 서버가 분류한 BTI 코드 (정확히 5글자) |
| is_correct | boolean | Y | `true` = "이 결과가 내 취향과 맞아요" → KNN 학습 데이터로 사용 |
| actual_preference | string | N | `is_correct: false`일 때 실제로 더 맞는 캐릭터명 입력 (선택) |

> 피드백 응답의 `storage` 필드로 저장 위치를 확인할 수 있습니다.  
> 피드백이 일정량 쌓이면 `python scripts/train_knn.py`로 KNN 모델을 학습시키세요.

**응답**
```json
{
  "status":         "success",
  "message":        "피드백이 저장되었습니다.",
  "storage":        "json",
  "total_feedback": 43
}
```

| 응답 필드 | 설명 |
|----------|------|
| `storage` | `"db"` = PostgreSQL 저장, `"json"` = 로컬 JSON 파일 저장 |
| `total_feedback` | 전체 누적 피드백 수 |

---

## 8. GET `/api/taste/profile/{user_id}`

저장된 사용자 취향 프로필 조회. 메모리 → DB 순서로 검색.

```bash
curl http://localhost:8000/api/taste/profile/user_001
```

**응답**: `/api/survey/convert` 응답과 동일한 구조 (status, taste_vector, bti_code, character_name, preferred_food_pairing 등).

**에러**
- 404: 프로필 없음 — `/api/survey/convert?user_id=...`를 먼저 호출해야 합니다.

---

## 9. POST `/api/recipe/suggest-sub-ingredients` ✦ Gemini

메인재료와 지역을 입력하면 지역 특산물 기반 서브재료 5개 추천.

**요청**
```json
{
  "main_ingredient": "쌀",
  "region":          "경기도"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| main_ingredient | string | Y | 주재료 (예: "쌀", "보리", "고구마") |
| region | string | N | 지역명 (예: "경기도", "제주"). 생략 시 `main_ingredient`로 자동 추론 (→ `GET /api/recipe/ingredient-region` 기준) |

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
  "title":           "봄날 딸기 막걸리",
  "main_ingredient": "쌀",
  "sub_ingredients": ["논산 딸기", "꿀"],
  "abv_range":       "5-7%"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| title | string | Y | 전통주 이름 또는 프로젝트 제목 |
| main_ingredient | string | Y | 주재료 |
| sub_ingredients | string[] | N | 서브재료 목록 |
| abv_range | string | N | 예상 도수 범위 (예: "5-7%", "10-13%") |

**응답**
```json
{ "flavor_tags": ["달콤한", "새콤한", "과일향", "청량한", "부드러운"] }
```

---

## 11. POST `/api/recipe/suggest-summary` ✦ Gemini

레시피 및 펀딩 프로젝트의 3문장 요약문 자동 생성.

**요청**
```json
{
  "title":           "봄날 딸기 막걸리",
  "main_ingredient": "쌀",
  "sub_ingredients": ["논산 딸기"],
  "abv_range":       "5-7%",
  "flavor_tags":     ["달콤한", "새콤한"],
  "concept":         "봄의 설레임을 담은 막걸리"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| title | string | Y | 전통주 이름 |
| main_ingredient | string | Y | 주재료 |
| sub_ingredients | string[] | N | 서브재료 목록 |
| abv_range | string | N | 도수 범위 |
| flavor_tags | string[] | N | 맛 태그 (suggest-flavor-tags 결과 활용 가능) |
| concept | string | N | 기획 콘셉트 또는 스토리 |

**응답**
```json
{ "summary": "논산 딸기의 새콤달콤함을 그대로 담은 봄날 한정 막걸리입니다. 부드러운 쌀 베이스에 딸기의 향긋함이 조화를 이룹니다. 봄 소풍이나 야외 모임에 어울리는 가벼운 전통주입니다." }
```

---

## 12. POST `/api/recipe/validate` ✦ Gemini

Gemini 양조 전문가가 레시피 제작 가능성을 분석하고 점수화.  
동일 입력에 1시간 캐시 적용.

**요청**
```json
{
  "title":           "제주 감귤 막걸리",
  "main_ingredient": "쌀",
  "sub_ingredients": ["제주 감귤", "유기농 설탕"],
  "abv_range":       "6-8%",
  "flavor_tags":     ["새콤달콤", "청량한"],
  "description":     "제주 감귤로 만든 상큼한 막걸리"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| title | string | Y | 전통주 이름 |
| main_ingredient | string | Y | 주재료 |
| sub_ingredients | string[] | N | 서브재료 목록 |
| abv_range | string | N | 도수 범위 |
| flavor_tags | string[] | N | 맛 태그 |
| description | string | N | 전통주 설명 |

**응답**
```json
{
  "feasibility":   "high",
  "score":         85,
  "issues":        [],
  "suggestions":   ["감귤 껍질 일부 사용 시 향이 더 풍부해집니다"],
  "summary":       "산미와 감귤향의 조합이 자연스러운 고품질 막걸리 레시피입니다.",
  "cached":        false
}
```

| feasibility | 기준 | 의미 |
|-------------|------|------|
| `high` | score ≥ 70 | 제작 가능성 높음 |
| `medium` | score 40~69 | 일부 조정 필요 |
| `low` | score < 40 | 재료·도수 재검토 필요 |

---

## 13. POST `/api/recipe/register`

레시피를 등록하고 추천 풀(`pool: "recipe"`)에 자동 편입.  
`taste_input` 미입력 시 Gemini가 자동으로 맛벡터 생성 (`GEMINI_AVAILABLE: true` 필요).

**요청**
```json
{
  "recipe_id":       "recipe_001",
  "user_id":         "user_001",
  "title":           "봄날 딸기 막걸리",
  "main_ingredient": "쌀",
  "sub_ingredients": ["논산 딸기", "꿀"],
  "abv_range":       "5-7%",
  "flavor_tags":     ["달콤한", "새콤한"],
  "description":     "봄의 설레임을 담은 딸기 막걸리",
  "taste_input": {
    "sweetness": 7, "body": 4, "carbonation": 4,
    "flavor": 8, "alcohol": 3, "acidity": 6,
    "aroma_intensity": 7, "finish": 5
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| recipe_id | string | Y | 레시피 고유 ID |
| user_id | string | Y | 레시피 작성자 ID |
| title | string | Y | 전통주 이름 |
| main_ingredient | string | Y | 주재료 |
| sub_ingredients | string[] | N | 서브재료 목록 |
| abv_range | string | N | 도수 범위 (예: "5-7%") |
| flavor_tags | string[] | N | 맛 태그 |
| description | string | N | 전통주 설명 |
| taste_input | TasteVector | N | 맛벡터 직접 입력. 없으면 Gemini 자동 생성 |

**응답**
```json
{
  "status":       "success",
  "recipe_id":    "recipe_001",
  "title":        "봄날 딸기 막걸리",
  "taste_vector": { "sweetness": 7.0, "body": 4.0, "carbonation": 4.0, "flavor": 8.0, "alcohol": 3.0, "acidity": 6.0, "aroma_intensity": 7.0, "finish": 5.0 },
  "source":       "direct_input",
  "message":      "레시피가 추천 풀에 편입되었습니다."
}
```

`source`: `"direct_input"` | `"gemini_auto"`

---

## 14. POST `/api/law/filter` ✦ Gemini

콘텐츠(펀딩 설명, 제품 소개)의 주류광고 법률 위반 여부 검토.  
동일 입력에 1시간 캐시 적용.

**요청**
```json
{
  "content_type": "product_description",
  "title":        "숙취 해소 막걸리",
  "description":  "이 막걸리는 숙취 해소에 효능이 있습니다",
  "ingredients":  ["쌀", "누룩"]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| content_type | string | Y | `"product_description"` (제품 소개/펀딩 설명) 또는 `"recipe"` (레시피 페이지) |
| title | string | Y | 콘텐츠 제목 |
| description | string | Y | 콘텐츠 본문 |
| ingredients | string[] | N | 재료 목록 |
| target_region | string | N | 타겟 지역 (지역 규정 추가 검토 시) |

**응답**
```json
{
  "violation": true,
  "details": [
    {
      "category": "건강기능식품 효능 주장",
      "law":      "식품위생법 제4조",
      "reason":   "'숙취 해소 효능'은 허가받지 않은 의약품적 효능 주장입니다.",
      "article":  "제4조 (위해 식품 등의 판매 등 금지)"
    }
  ],
  "recommendation": "효능 표현을 삭제하고 맛과 향으로만 설명해주세요."
}
```

---

## 15. GET `/api/law/info`

서버에 내장된 전통주 관련 법령 목록 조회 (Gemini 미사용).

```bash
curl http://localhost:8000/api/law/info
```

**응답**
```json
{
  "status": "success",
  "laws": [
    {
      "name":        "주세법",
      "law_id":      "LAW001",
      "keywords":    ["주류", "제조", "면허"],
      "description": "주류 제조 및 판매에 관한 기본법"
    }
  ]
}
```

---

## 16. GET `/api/insight`

추천 데이터 기반 인사이트 대시보드. 기간별 취향 트렌드·인기 전통주 통계 제공.

```bash
curl "http://localhost:8000/api/insight?period=week"
```

| 쿼리 파라미터 | 값 | 기본값 | 설명 |
|---------------|-----|--------|------|
| period | `day` \| `week` \| `month` | `week` | 집계 기간 |

**응답**
```json
{
  "period":       "week",
  "top_drinks":   [],
  "taste_trends": {},
  "ai_report":    "이번 주는 산미 높은 막걸리 선호도가 증가했습니다."
}
```

---

## 17. POST `/api/chat` ✦ Gemini

전통주(막걸리·청주·탁주·약주) 관련 질문에 답변하는 챗봇.  
비관련 질문은 Gemini 호출 없이 즉시 거절.

**요청**
```json
{
  "message": "막걸리 초보자에게 추천하는 도수는?",
  "user_id": "user_001",
  "history": [
    { "role": "user",      "content": "막걸리가 뭔가요?" },
    { "role": "assistant", "content": "막걸리는 쌀을 발효시킨 한국 전통주입니다." }
  ]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| message | string | Y | 사용자 질문 |
| user_id | string | N | 사용자 ID (대화 맥락 저장용) |
| history | array | N | 이전 대화 기록. `role`: `"user"` 또는 `"assistant"` |

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

## 18. POST `/api/chat/stream` ✦ Gemini

전통주 관련 질문에 SSE(Server-Sent Events)로 스트리밍 응답.

**요청**
```json
{
  "message":    "막걸리와 약주의 차이가 뭔가요?",
  "session_id": "session_abc123"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| message | string | Y | 사용자 질문 |
| session_id | string | N | 세션 ID (같은 ID 재사용 시 대화 맥락 유지) |

**응답** `Content-Type: text/event-stream`

```
data: {"type": "chunk", "content": "막걸리는 "}

data: {"type": "chunk", "content": "쌀, 물, 누룩으로 만든"}

data: {"type": "done",  "content": "", "full_response": "막걸리는 쌀, 물, 누룩으로 만든 탁주입니다."}
```

| type | 설명 |
|------|------|
| `chunk` | 스트리밍 텍스트 조각 |
| `done` | 스트리밍 완료. `full_response`에 전체 텍스트 포함 |
| `off_topic` | 전통주 무관 질문 거절 |
| `error` | 오류 발생 |

**에러**
- 503: `GEMINI_AVAILABLE: false`일 때

---

## 19. POST `/api/drinks/request`

DB에 없는 전통주를 관리자 승인 방식으로 등록 요청.  
승인 전까지 추천 풀에 포함되지 않습니다.

**요청**
```json
{
  "name":        "양평 더 쌀 막걸리",
  "brewery":     "양평양조장",
  "region":      "경기 양평",
  "abv":         6.0,
  "description": "양평 지역 쌀로 빚은 막걸리",
  "user_id":     "user_001"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| name | string | Y | 전통주 이름 |
| brewery | string | N | 양조장 이름 |
| region | string | N | 생산 지역 |
| abv | float | N | 도수 (예: 6.0) |
| description | string | N | 전통주 설명 |
| user_id | string | Y | 요청자 ID |

**응답**
```json
{
  "status":     "success",
  "request_id": "req_20260522_001",
  "message":    "등록 요청이 접수되었습니다. 검토 후 추가됩니다."
}
```

---

## 20. GET `/api/drinks/requests`

전통주 등록 요청 목록 전체 조회 (관리자 용도).

```bash
curl http://localhost:8000/api/drinks/requests
```

**응답**
```json
{
  "requests": [
    {
      "request_id": "req_20260522_001",
      "name":       "양평 더 쌀 막걸리",
      "brewery":    "양평양조장",
      "status":     "pending",
      "created_at": "2026-05-22T10:00:00"
    }
  ]
}
```

---

## 21. POST `/api/drinks/requests/{request_id}/approve`

등록 요청을 승인하고 전통주를 `pool: "approved"` 추천 풀에 추가.

```bash
curl -X POST http://localhost:8000/api/drinks/requests/req_20260522_001/approve
```

**응답**
```json
{
  "status":  "success",
  "message": "양평 더 쌀 막걸리가 추천 풀에 추가되었습니다."
}
```

---

## 22. POST `/api/funding/register`

펀딩 전통주를 등록하고 `pool: "funding"` 추천 풀에 편입 (`is_funding: true` 마킹).  
`taste_input` 미입력 시 Gemini가 자동으로 맛벡터 생성.

**요청**
```json
{
  "funding_id":       "funding_001",
  "name":             "한라봉 막걸리",
  "brewery":          "제주양조장",
  "brewery_user_id":  "brewer_001",
  "region":           "제주",
  "abv":              7.0,
  "main_ingredient":  "쌀",
  "description":      "제주 한라봉을 넣은 상큼한 막걸리",
  "taste_input": {
    "sweetness": 6, "body": 4, "carbonation": 5,
    "flavor": 8, "alcohol": 4, "acidity": 7,
    "aroma_intensity": 7, "finish": 5
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| funding_id | string | Y | 펀딩 고유 ID (중복 불가) |
| name | string | Y | 전통주 이름 |
| brewery | string | N | 양조장 이름 |
| brewery_user_id | string | N | 양조장/기획자 ID |
| region | string | N | 생산 지역 |
| abv | float | Y | 도수 (0~100) |
| main_ingredient | string | N | 주재료 |
| description | string | N | 전통주 설명 |
| taste_input | TasteVector | N | 맛벡터 직접 입력. 없으면 Gemini 자동 생성 |

**응답**
```json
{
  "status":       "success",
  "funding_id":   "funding_001",
  "name":         "한라봉 막걸리",
  "taste_vector": { "sweetness": 6.0, "body": 4.0, "carbonation": 5.0, "flavor": 8.0, "alcohol": 4.0, "acidity": 7.0, "aroma_intensity": 7.0, "finish": 5.0 },
  "source":       "direct_input",
  "message":      "펀딩 전통주가 추천 풀에 편입되었습니다."
}
```

**에러**
- 400: 이미 등록된 `funding_id`
- 400: `abv`가 0~100 범위 밖

---

## 23. GET `/api/funding/{funding_id}`

등록된 펀딩 전통주의 정보와 맛벡터 조회.

```bash
curl http://localhost:8000/api/funding/funding_001
```

**응답**
```json
{
  "funding_id":      "funding_001",
  "name":            "한라봉 막걸리",
  "brewery":         "제주양조장",
  "region":          "제주",
  "description":     "제주 한라봉을 넣은 상큼한 막걸리",
  "abv":             7.0,
  "main_ingredient": "쌀",
  "brewery_user_id": "brewer_001",
  "taste_vector":    { "sweetness": 6.0, "body": 4.0, "carbonation": 5.0, "flavor": 8.0, "alcohol": 4.0, "acidity": 7.0, "aroma_intensity": 7.0, "finish": 5.0 },
  "registered_at":   "2026-05-22T10:00:00"
}
```

**에러**
- 404: 존재하지 않는 `funding_id`

---

## 24. POST `/api/funding/{funding_id}/taste-update`

샘플 시음 후 맛벡터를 보정하고 추천 풀에 즉시 반영.  
초기 등록 맛벡터를 실제 시음 결과로 덮어씁니다.

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

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| taste_input | TasteVector | Y | 시음 후 실측 맛벡터 (0.0~10.0) |

**응답**
```json
{
  "status":       "success",
  "funding_id":   "funding_001",
  "taste_vector": { "sweetness": 7.0, "body": 4.0, "carbonation": 5.0, "flavor": 8.0, "alcohol": 4.0, "acidity": 6.0, "aroma_intensity": 7.0, "finish": 5.0 },
  "message":      "맛벡터가 보정되어 추천 풀에 반영되었습니다."
}
```

**에러**
- 404: 존재하지 않는 `funding_id`

---

## 25. POST `/api/image/generate` ✦ Gemini

전통주 정보를 기반으로 Gemini가 영문 프롬프트를 생성한 후  
`gemini-2.5-flash-image` 모델로 이미지를 직접 생성.  
Gemini 실패 시 `HUGGINGFACE_TOKEN`이 있으면 Stable Diffusion으로 fallback.

**요청**
```json
{
  "name":        "이천 쌀 막걸리",
  "description": "이천 쌀로 만든 달콤한 막걸리",
  "flavor_tags": ["달콤한", "고소한"],
  "region":      "경기도 이천"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| name | string | Y | 전통주 이름 |
| description | string | Y | 전통주 설명 |
| flavor_tags | string[] | N | 맛 태그 (이미지 스타일에 반영) |
| region | string | N | 지역 (지역 특색 반영) |

**응답 — 이미지 생성 성공**
```json
{
  "status":      "success",
  "image_base64": "iVBORw0KGgoAAAANS...",
  "mime_type":   "image/png",
  "model_used":  "gemini-2.5-flash-image",
  "prompt_used": "A traditional Korean ceramic cup filled with milky-white Icheon rice makgeolli, placed on a hanji-covered surface with bamboo and celadon props, warm natural light, premium product photography.",
  "message":     "Gemini gemini-2.5-flash-image로 이미지 생성 완료"
}
```

**응답 — 이미지 생성 실패 (프롬프트만 반환)**
```json
{
  "status":      "prompt_only",
  "prompt_used": "A traditional Korean ceramic cup...",
  "model_used":  "none",
  "message":     "이미지 생성 실패. HUGGINGFACE_TOKEN 또는 Gemini 이미지 모델 권한을 확인하세요."
}
```

| status | 의미 |
|--------|------|
| `success` | 이미지 생성 완료 (`image_base64` + `mime_type` 포함) |
| `prompt_only` | 이미지 생성 실패, 프롬프트만 반환 |
| `disabled` | `GEMINI_API_KEY` 미설정 |
| `error` | 생성 중 오류 |

**에러**
- 503: `GEMINI_AVAILABLE: false`일 때

---

## 26. GET `/api/recipe/ingredient-region`

재료명을 입력하면 지리적 표시제 기준 생산 지역 목록을 반환. **Gemini 호출 없음 (즉시 응답)**.

```bash
curl "http://localhost:8000/api/recipe/ingredient-region?ingredient=쌀"
```

| 쿼리 파라미터 | 타입 | 필수 | 설명 |
|---------------|------|------|------|
| ingredient | string | Y | 재료명 (예: "이천 쌀", "감귤", "딸기") |

**응답 — 매핑 성공**
```json
{
  "ingredient":   "쌀",
  "regions":      ["경기도 이천", "강원도 철원", "전라북도 김제"],
  "found":        true,
  "data_source":  "manual"
}
```

**응답 — 매핑 없음**
```json
{
  "ingredient":  "통밀",
  "regions":     [],
  "found":       false,
  "data_source": "manual"
}
```

| 필드 | 설명 |
|------|------|
| `regions` | 생산 지역 배열. 매핑 없으면 빈 배열 `[]` |
| `found` | `true` = 1개 이상 지역 매핑 성공 |
| `data_source` | `"manual"` = 하드코딩 테이블. 향후 `"api"` (농사로 공공 API) 전환 예정 |

> `regions[0]`이 `/api/recipe/suggest-sub-ingredients` 지역 자동추론에 사용됩니다.

**지원 재료 예시**

| 재료 | 추론 지역 (복수 가능) |
|------|---------------------|
| 쌀 | 경기도 이천, 강원도 철원, 전라북도 김제 |
| 사과 | 경상북도 청송, 충청북도 충주, 경상남도 거창 |
| 딸기 | 충청남도 논산, 경상남도 진주 |
| 감귤, 한라봉 | 제주도 |
| 잣 | 경기도 가평 |
| 인삼, 홍삼 | 충청남도 금산, 경상북도 영주 |
| 녹차 | 전라남도 보성 |
| 포도 | 경상북도 영천, 충청북도 영동 |

---

## 27. POST `/api/brewery/verify-ocr` ✦ Gemini

양조장 인증 서류 이미지를 분석하여 3종 서류 판별 및 정보 추출.

**인정 서류 3종**
1. 주류제조면허증 (국세청 발급)
2. 사업자등록증 (국세청 발급)
3. 식품제조가공업 영업신고증 (식약처 / 지자체 발급)

**요청**
```json
{
  "image_base64": "/9j/4AAQSkZJRgABAQ...",
  "mime_type":    "image/jpeg"
}
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| image_base64 | string | Y | — | 이미지 base64 인코딩 문자열 |
| mime_type | string | N | `image/jpeg` | `image/jpeg` 또는 `image/png` |

**응답 — 유효 서류**
```json
{
  "status":        "success",
  "is_valid":      true,
  "document_type": "주류제조면허증",
  "confidence":    "high",
  "extracted": {
    "document_type":       "주류제조면허증",
    "is_valid_document":   true,
    "brewery_name":        "한강양조 주식회사",
    "registration_number": "서울-주류-2024-001",
    "owner_name":          "홍길동",
    "address":             "서울특별시 마포구 양화로 100",
    "issue_date":          "2024-01-15",
    "issuing_authority":   "국세청",
    "alcohol_types":       ["탁주", "약주"],
    "confidence":          "high",
    "rejection_reason":    null
  }
}
```

**응답 — 유효하지 않은 서류**
```json
{
  "status":        "success",
  "is_valid":      false,
  "document_type": "인식불가",
  "confidence":    "low",
  "extracted": {
    "is_valid_document": false,
    "rejection_reason":  "인정되는 3종 서류(주류제조면허증, 사업자등록증, 식품제조가공업영업신고증)에 해당하지 않습니다."
  }
}
```

| 응답 필드 | 설명 |
|----------|------|
| `is_valid` | `true` = 3종 서류 중 하나로 인식됨 |
| `document_type` | 판별된 서류 종류 |
| `confidence` | `high` / `medium` / `low` — OCR 신뢰도 |
| `extracted.alcohol_types` | 주류제조면허증인 경우 제조 가능 주종 목록 |

**에러**
- 400: `image_base64` 누락
- 503: `GEMINI_AVAILABLE: false` 또는 `GEMINI_API_KEY` 미설정

---

## 주요 흐름 요약

### 신규 사용자 추천 흐름
```
1. POST /api/survey/convert?user_id=XXX
        ↓ 맛벡터 + BTI 코드 + preferred_food_pairing 저장
2. POST /api/recommend { "user_id": "XXX", "top_k": 5 }
        ↓ 저장된 프로필의 taste_vector + preferred_food_pairing 자동 적용
        ↓ 앙상블: taste 65% + ingredient 15% + region 10% + food 10%
        ↓ 동일 양조장 최대 2개 제한 (다양성 확보)
        ↓ 펀딩 전통주 최소 1개 보장 (pool="all" 시)
3. POST /api/taste/update (시음 후 별점/축별 평가)
        ↓ 이후 recommend 호출 시 진화된 맛벡터 자동 사용
4. POST /api/bti/feedback { "is_correct": true/false }
        ↓ 피드백 누적 → scripts/train_knn.py 실행 → KNN 모델 활성화
```

### 펀딩 전통주 등록 흐름
```
1. POST /api/recipe/suggest-sub-ingredients   ← 지역 특산물 서브재료 추천
2. POST /api/recipe/suggest-flavor-tags       ← 맛 태그 추천
3. POST /api/recipe/validate                  ← 제작 가능성 점수 확인 (score ≥ 70 권장)
4. POST /api/law/filter                       ← 광고 문구 법률 검토 (violation=false 확인)
        ↓
5. POST /api/funding/register                 ← 추천 풀 편입 (is_funding=true)
        ↓ 시음 샘플 완성 후
6. POST /api/funding/{id}/taste-update        ← 실측 맛벡터로 정밀 보정
```

### KNN BTI 모델 고도화 흐름
```
1. 사용자들의 /api/bti/feedback 피드백 누적 (is_correct=true 데이터)
2. python scripts/train_knn.py 실행 (10개 이상 시 학습 가능, 50개 권장)
        ↓ models/knn_bti_model.pkl 생성
3. 서버 재시작 → KNN 모델 자동 로드
4. GET /health 에서 knn_model_loaded: true 확인
5. POST /api/survey/convert 응답의 bti_method: "knn" 으로 전환
```
