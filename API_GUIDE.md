# 주담 AI 서버 — API 가이드

**Public Base URL** `http://43.201.97.229:8000`<br>
**Private Base URL** `http://10.0.1.83:8000`<br>
**Local Base URL** `http://localhost:8000`<br>
**Version** `0.3.0`<br>
**기본 Content-Type** `application/json` (`/api/brewery/verify-ocr`만 `multipart/form-data`)

> 검증 기준: 현재 작업 브랜치의 `app/main.py`, `app/chat.py`, `app/models.py`와 관련 구현·테스트를 직접 대조했습니다. 작성 환경에는 실행 가능한 Python/pytest가 없고 Public/Private 서버도 연결되지 않아, 응답 예시는 코드의 고정 반환값 또는 저장소 테스트 fixture 기준입니다. 라이브 미검증 항목은 별도로 표시합니다.

---

## 환경 변수 & 서버 실행

`.env` 파일을 프로젝트 루트에 두고 아래 키를 설정합니다 (`.env`는 절대 커밋 금지 — `.gitignore` 처리됨).

```bash
# .env (예시 — 실제 키 값으로 교체)
GEMINI_API_KEY=발급받은_제미나이_키        # 레시피/법률/챗봇/이미지/OCR 등 Gemini 기능 필수
LAW_API_KEY=국가법령정보센터_키             # /api/law/* (없으면 내장 법령 fallback)
NONGSARO_API_KEY=농사로_공공API_키          # scripts/collect_local_products.py (지역특산물 수집)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/juddam   # 없으면 인메모리/JSON fallback
REDIS_URL=redis://localhost:6379            # 선택 (캐시)
HUGGINGFACE_TOKEN=                          # 선택 (이미지 생성 Gemini 실패 시 SD fallback)
AWS_REGION=ap-northeast-2                   # 선택 (app/sqs_worker.py 실행 시 필수)
AWS_SQS_AI_TASK_QUEUE_URL=https://...        # 선택 (app/sqs_worker.py 실행 시 필수)
LOG_LEVEL=INFO
PORT=8000
```

| 변수 | 필수 | 용도 | 미설정 시 |
|------|------|------|----------|
| `GEMINI_API_KEY` | ★ | Gemini 기반 기능(✦ 표시: 레시피·법률 보강·챗봇·이미지·OCR 등) | 챗봇 본문·후속질문과 서브재료 선별은 안전 폴백, 그 외 기능은 503/`disabled` 가능 |
| `LAW_API_KEY` | 권장 | 국가법령정보센터 연동 | 내장 법령 목록으로 동작 |
| `NONGSARO_API_KEY` | 선택 | 농사로 지역특산물 수집 스크립트 | 하드코딩 지역 매핑 fallback |
| `DATABASE_URL` | 선택 | PostgreSQL 영속화 | 인메모리 + JSON 파일 fallback |
| `REDIS_URL` / `HUGGINGFACE_TOKEN` | 선택 | 캐시 / 이미지 SD fallback | 기능 생략 |
| `AWS_REGION` / `AWS_SQS_AI_TASK_QUEUE_URL` | 선택 | `app/sqs_worker.py` SQS 워커 | API 서버 실행에는 불필요 |

> 키 목록 템플릿은 `.env.example` 참고(실제 값 없는 플레이스홀더). 법령 RAG 임베딩 모델은 `LAW_EMBED_MODEL`(기본 `paraphrase-multilingual-MiniLM-L12-v2`)로 교체 가능하며, 법령 API 호출 헤더는 `LAW_USER_AGENT`/`LAW_REFERER`로 override 가능합니다.

**실행**
```bash
# 의존성
pip install -r requirements.txt

# 개발 서버 (자동 리로드)
uvicorn app.main:app --reload --port 8000

# 상태 확인
curl http://localhost:8000/health
```

`GET /health` 의 `gemini_key_loaded` / `gemini_available` / `db_connected` / `knn_model_loaded` 로 환경 구성을 점검할 수 있습니다.

---

## 목차

| # | 메서드 | 경로 | 설명 | Gemini |
|---|--------|------|------|--------|
| 1 | GET | `/` | 서버 상태 확인 | |
| 2 | GET | `/health` | 헬스체크 (기능별 상태 + KNN 상태) | |
| 3 | POST | `/api/recommend` | 맛벡터 기반 전통주 추천 (8축 코사인 + 사실일치 가산, 95/99 캡) | |
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
| 27 | POST | `/api/brewery/verify-ocr` | 양조장 인증 서류 OCR (레지스트리 기반 7종) | ✓ |

### 기능별 분류

| 분류 | 엔드포인트 |
|------|-----------|
| 시스템 | `GET /` · `GET /health` |
| 설문/BTI | `POST /api/survey/convert` · `POST /api/bti/feedback` · `GET /api/taste/profile/{user_id}` |
| 추천/취향 | `POST /api/recommend` · `POST /api/taste/update` · `GET /api/taste/history/{user_id}` |
| 레시피 | `POST /api/recipe/suggest-sub-ingredients` · `suggest-flavor-tags` · `suggest-summary` · `validate` · `register` · `GET /api/recipe/ingredient-region` |
| 법률 | `POST /api/law/filter` · `GET /api/law/info` |
| 인사이트 | `GET /api/insight` |
| 챗봇 | `POST /api/chat` · `POST /api/chat/stream` |
| 전통주 등록 | `POST /api/drinks/request` · `GET /api/drinks/requests` · `POST /api/drinks/requests/{id}/approve` |
| 펀딩 | `POST /api/funding/register` · `GET /api/funding/{id}` · `POST /api/funding/{id}/taste-update` |
| 이미지 | `POST /api/image/generate` |
| OCR | `POST /api/brewery/verify-ocr` |

### 전체 라우트 계약 매트릭스

현재 `app/main.py`와 `app/chat.py`에서 선언된 라우트는 총 **27개**입니다. 모든 라우트는 현재 애플리케이션 내부 인증 의존성이나 Bearer/API key 검사를 사용하지 않습니다. 외부 공개 범위와 사용자·관리자 권한 검사는 백엔드/API Gateway에서 적용해야 합니다.

| 메서드 | 경로 | 요청 계약 | 응답 계약 | 형식 | 캐시 |
|---|---|---|---|---|---|
| GET | `/` | 없음 | inline object | JSON | 없음 |
| GET | `/health` | 없음 | inline object | JSON | 없음 |
| POST | `/api/recommend` | `RecommendRequest` | `List[RecommendResponse]` | JSON | 없음 |
| POST | `/api/taste/update` | `TasteUpdateRequest` | inline object | JSON | 없음 |
| GET | `/api/taste/history/{user_id}` | path `user_id: string` | inline object | JSON | 없음 |
| POST | `/api/survey/convert` | body `SurveyResponse`, query `user_id?: string` | `SurveyConvertResponse` | JSON | 없음 |
| POST | `/api/bti/feedback` | `BTIFeedbackRequest` | inline object | JSON | 없음 |
| GET | `/api/taste/profile/{user_id}` | path `user_id: string` | 저장된 survey profile | JSON | 없음 |
| POST | `/api/recipe/suggest-sub-ingredients` | `SubIngredientsRequest` | `SubIngredientsResponse` | JSON | 인메모리 1,440분 |
| POST | `/api/recipe/suggest-flavor-tags` | `FlavorTagsRequest` | `FlavorTagsResponse` | JSON | 없음 |
| POST | `/api/recipe/suggest-summary` | `SummaryRequest` | `SummaryResponse` | JSON | 없음 |
| POST | `/api/recipe/validate` | `RecipeValidateRequest` | `RecipeValidateResponse` | JSON | 인메모리 60분 |
| POST | `/api/recipe/register` | `RecipeRegisterRequest` | `RecipeRegisterResponse` | JSON | 없음 |
| POST | `/api/law/filter` | `LawFilterRequest` | inline object | JSON | 인메모리 60분 |
| GET | `/api/law/info` | 없음 | inline object | JSON | 없음 |
| GET | `/api/insight` | query `period: string = "week"` | inline insight object | JSON | 인메모리 60분 |
| POST | `/api/chat` | `ChatRequest` | `ChatResponse` | JSON | 없음 |
| POST | `/api/chat/stream` | `ChatStreamRequest` | SSE events | JSON 요청/SSE 응답 | 없음 |
| POST | `/api/drinks/request` | `DrinkRequestCreate` | inline object | JSON | 없음 |
| GET | `/api/drinks/requests` | query `status?: string = null` | inline object | JSON | 없음 |
| POST | `/api/drinks/requests/{request_id}/approve` | path `request_id: integer` | inline object | JSON | 없음 |
| POST | `/api/funding/register` | raw JSON 검증 후 `FundingRegisterRequest` 구성 | `FundingRegisterResponse` | JSON | 없음 |
| GET | `/api/funding/{funding_id}` | path `funding_id: string` | `FundingGetResponse` | JSON | 없음 |
| POST | `/api/funding/{funding_id}/taste-update` | path `funding_id`, body `FundingTasteUpdateRequest` | `FundingTasteUpdateResponse` | JSON | 없음 |
| POST | `/api/image/generate` | `ImageGenerateRequest` | inline object | JSON | 없음 |
| GET | `/api/recipe/ingredient-region` | query `ingredient: string` | inline object | JSON | 없음 |
| POST | `/api/brewery/verify-ocr` | multipart fields | inline OCR result | multipart/JSON | 없음 |

> 모델별 필드·타입·필수 여부·기본값은 각 엔드포인트 표가 권위 있는 계약입니다. Pydantic에서 기본값이 없거나 `...`인 필드는 필수입니다.

---

## 공통 사항

### 인증

AI 서버 코드에는 인증 미들웨어나 `Depends` 기반 권한 검사가 없습니다. 따라서 현재는 모든 엔드포인트가 AI 서버 관점에서 인증 없이 호출 가능합니다. 특히 관리자용 `/api/drinks/requests*`, OCR, 사용자 프로필·취향 API는 백엔드 또는 API Gateway에서 인증·인가 후 호출해야 합니다.

### 술BTI 코드 구조 (5글자)

`[단맛 S/D][바디 H/L][탄산 F/M][풍미 U/C][도수 H/L]`

| 축 | 문자 의미 | 조건 |
|----|----------|------|
| 단맛 (S/D) | S = Sweet, D = Dry | sweetness ≥ 5 → S |
| 바디 (H/L) | H = Heavy, L = Light | body ≥ 5 → H |
| 탄산 (F/M) | F = Fizzy, M = Mellow | carbonation ≥ 5 → F |
| 풍미 (U/C) | U = Unique, C = Classic | flavor ≥ 5 → U |
| 도수 (H/L) | H = High, L = Low | alcohol ≥ 5.5 → H |

> **도수 임계값은 5.5** (과거 9에서 변경). alcohol 축은 실제 ABV(도수)가 아니라 0~10 스케일의 파생 점수이며, 설문 Q2 ③(9~12도, 고도수) 응답이 H로 분류되도록 보정한 값입니다.

> **5글자 vs 4글자** — 서버 `/api/survey/convert` 응답의 `bti_code`는 **5글자**(도수 포함)입니다. 별도의 정적 설문 페이지(`web/survey/index.html`)는 동일한 8축 맛벡터에서 **앞 4글자만**(도수 제외, `bti4`) 사용합니다. 두 체계 모두 단맛/바디/탄산/풍미 임계는 5, 4글자는 도수축만 생략한 부분집합입니다.

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

현재 에러 응답은 호출 경로에 따라 다음 세 형태가 존재합니다.

**`raise_api_error`를 사용하는 Gemini 경로**
```json
{ "detail": "현재 AI 서비스가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요." }
```

Gemini quota/resource-exhausted 또는 AI 연결 오류는 HTTP 503, 나머지는 HTTP 500과 엔드포인트별 일반 메시지로 반환합니다. 내부 예외 메시지는 `raise_api_error` 경로에서 클라이언트에 노출하지 않습니다.

**일반 `HTTPException` 및 Pydantic 검증**
```json
{ "detail": "오류 설명 또는 구조화된 오류 객체" }
```

`RequestValidationError` 응답은 파일 bytes를 그대로 포함하지 않고 `"<N bytes omitted>"` 형태로 마스킹합니다.

**커스텀 404/500 핸들러**
```json
{ "status": "error", "message": "요청한 경로를 찾을 수 없습니다." }
```

| HTTP 코드 | 의미 |
|---|---|
| 400 | 명시적 요청 파라미터·업무 규칙 오류 |
| 404 | 리소스 또는 경로 없음 |
| 422 | FastAPI/Pydantic 필드 타입·필수값·범위 검증 실패 |
| 503 | Gemini 점검·혼잡 또는 필수 키 미설정 경로 |
| 500 | 서버 내부 오류 |
| 200 + `body.status="FAILED"` | OCR 업무 실패. 인증 신청 비차단 정책 |

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

**매칭 % (`similarity_percent`) 산출**

- 매칭 %는 **사용자와 제품의 8축 취향 벡터 코사인 유사도**를 기반으로 한다. (재료·지역·음식 가중합이 아님)
- 취향 코사인은 표시 시 **최대 95%로 캡**한다 ("100% 매칭" 단정 회피).
- 사용자 프로필에 명시된 선호가 제품과 **"사실 일치"** 할 때만 소폭 가산한다 (추정이 아닌 사실 일치만):

| 가산 항목 | 조건 | 가산값 |
|-----------|------|--------|
| 선호 과일 | `preferred_fruit`(끝 '류'는 어간 매칭: 감귤류→감귤, 베리류→베리)가 제품 `ingredients`에 포함 | **+3%p** |
| 선호 도수 | `preferred_abv` 구간(예: 7~9도)에 제품 `abv`가 들어감 | **+2%p** |

- 가산 포함 **최종 상한은 99%** (100%는 표시되지 않음, 최대 가산 +5%p).
- 정렬은 표시 % 기준이므로 **표시 % 순서 = 목록 순서**.
- `similarity`는 raw 코사인(0~1) 그대로 반환하고, `similarity_percent`만 위 방식(캡 + 사실일치 가산)으로 산출한다. **요청/응답 스키마는 변경 없음**(내부 산출만 변경).

> `food_pairing` / `weights`는 요청 필드로 받기는 하지만 **현재 매칭 % 계산에는 사용하지 않는다** (취향 코사인 + 사실 일치 가산만 반영).

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
| weights | object | N | null | (구) 앙상블 가중치. **현재 매칭 % 계산에 미사용** (취향 코사인 + 사실 일치 가산만 반영) |

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
| `similarity_percent` | 8축 취향 코사인 % (최대 95 캡) + 사실 일치 가산(선호과일 +3 / 선호도수 +2), 최종 상한 99 |
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
| q7 | Likert | 1~7 | 과일 향 선호도 |
| q8 | Likert | 1~7 | 여운 선호도 (1=깔끔하게 끝남, 7=긴 여운) |
| q9 | Likert | 1~7 | 향 복잡도 선호도 (1=단순한 향, 7=복잡한 향) |
| q10 | Likert | 1~7 | 식감 선호도 (1=물처럼 맑음, 7=걸쭉함) |
| q11 | Likert | 1~7 | 색상 선호도 (1=맑은 투명, 7=불투명 탁함) |
| q12 | Likert | 1~7 | 도수에 대한 민감도 (1=도수 낮을수록 좋음, 7=높을수록 좋음) |
| q13 | Likert | 1~7 | 알콜 감지 선호도 |
| q14 | Likert | 1~7 | 탄산감 필요 정도 (1=전혀 불필요, 7=꼭 있어야 함) |
| q15 | Likert | 1~7 | 향 강도 선호도 (1=향 없는 것, 7=향 아주 강한 것) |
| q16 | Likert | 1~7 | 꽃향 선호도 |
| q17 | Likert | 1~7 | 허브향 선호도 |
| q18 | Likert | 1~7 | 과일/꽃 향 선호도 (1=전혀 불필요, 7=과일·꽃향 필수) |
| q19 | Likert | 1~7 | 신선한 향 선호도 |
| q20 | Likert | 1~7 | 구수한 향 선호도 |
| q21 | Likert | 1~7 | 알코올 느낌 선호도 (1=알코올 느낌 싫음, 7=알코올 느낌 좋음) |
| q22 | Likert | 1~7 | 전반적인 맛 강도 선호도 |
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
  "is_correct":         false,
  "actual_preference":  null,
  "wrong_axes":         ["단맛", "바디감·묵직함"],
  "feedback_reason":    "실제로는 조금 더 드라이하고 가벼운 취향입니다."
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| user_id | string | Y | 사용자 ID (1~50자). 해당 사용자의 `taste_vector`가 함께 저장됨 |
| bti_code | string | Y | 서버가 분류한 BTI 코드 (정확히 5글자) |
| is_correct | boolean | Y | `true` = "이 결과가 내 취향과 맞아요" → KNN 학습 데이터로 사용 |
| actual_preference | string | N | `is_correct: false`일 때 실제로 더 맞는 캐릭터명 입력 (선택) |
| wrong_axes | string[] | N | `is_correct: false`일 때 틀린 축 복수 선택. 예: 단맛, 바디감·묵직함, 탄산감, 풍미·향, 잘 모르겠음 |
| feedback_reason | string | N | 자유 텍스트 이유 |

> 피드백 응답의 `storage` 필드로 저장 위치를 확인할 수 있습니다.  
> 피드백이 일정량 쌓이면 `python scripts/train_knn.py`로 KNN 모델을 학습시키세요.
>
> `wrong_axes`와 `feedback_reason`은 현재 요청·메모리 entry 및 JSON fallback 수집용입니다. `bti_feedback` DB 테이블에는 해당 컬럼이 없어 DB 저장 시 적재되지 않으며, KNN 학습에도 사용되지 않습니다.
> 자유 텍스트 이유를 `actual_preference`에 넣지 마세요. `actual_preference`는 현재 `original_code`로 매핑되며 DB 컬럼 길이는 `VARCHAR(10)`입니다.

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

## 9. POST `/api/recipe/suggest-sub-ingredients`

메인재료와 지역을 별도로 입력하면 실제 수집 데이터에서 확인된 지역 특산물 후보를 최대 5개 반환합니다.
후보가 2개 이상이고 `GEMINI_API_KEY`가 있으면 Gemini가 후보 목록 안에서 궁합이 좋은 재료를 보조 선별합니다.
Gemini가 목록에 없는 특산물명을 생성할 수 없도록 결과를 실제 후보 목록과 대조하며, 호출·파싱·대조 실패 시 기존 후보 최대 5개로 폴백합니다. 응답 모델은 선별 여부와 무관하게 동일합니다.

**요청**
```json
{
  "main_ingredient": "사과",
  "region":          "청주시"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| main_ingredient | string | Y | 주재료. `snake_case`가 공식 계약. 기존 `mainIngredient`는 임시 alias 호환 |
| region | string | N | 사용자가 직접 입력하는 값이 아니라, **26번 `GET /api/recipe/ingredient-region` 응답의 `regions` 중 사용자가 선택한 값**. 누락 시 500 대신 `data_source: "unavailable"` 반환. 2단계 흐름은 26번 참조 |

**응답**
```json
{
  "sub_ingredients": ["쌀", "딸기", "포도", "복숭아", "고구마"],
  "region": "청주시",
  "data_source": "nongsaro_api",
  "traditional_liquor_status": "NEEDS_REVIEW",
  "warnings": ["지역특산주 요건 충족 여부는 별도 법률·면허 검토가 필요합니다."]
}
```

| `data_source` | 의미 |
|---|---|
| `nongsaro_api` | `local_products.json`의 농사로 수집 결과에서 확인 |
| `manual` | 코드의 수동 매핑에서 확인 |
| `unavailable` | 입력 지역에서 확인 가능한 후보 없음 또는 region 누락 |

지역특산주 요건은 재료 매칭만으로 확정하지 않으며 현재 응답은 `NEEDS_REVIEW`입니다.
Gemini 선별 여부는 현재 응답 필드로 구분하지 않습니다.

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

**3등급 판정(`verdict`)** — 자동 차단/통과를 강제하지 않고 애매한 건 사람이 본다:

| `verdict` | 의미 | `violation` |
|-----------|------|-------------|
| `block` | 명백한 위반 → 자동 차단 | `true` |
| `pass` | 명백히 정상 → 자동 통과 | `false` |
| `review` | 애매 → **관리자 검토 큐로** (자동 차단·통과 안 함) | `false` |

> `violation`(bool)은 하위호환 필드로 **`block`일 때만 `true`**입니다. `review`는 `violation:false`이되 `verdict:"review"`이므로, 클라이언트는 `verdict`로 분기해 `review`를 검토 대기열로 보내세요.

**검토 파이프라인**: ① 위반 키워드 1차 즉시차단(QUICK) → ② 법령 RAG 검색(관련 조문 컨텍스트) → ③ **모든 콘텐츠를 Gemini로 1회 검토**(키워드 미일치도 검토 — 무검토 통과 경로 없음). Gemini 실패 시 키워드 결과 fallback(위반 키워드 있으면 `block`, 없으면 `review` 보류).

**펀딩 콘텐츠 판정 기준** (`content_type`이 펀딩/제품설명일 때):
- 전통주 제조·판매 **리워드형 펀딩(후원 대가로 제품/굿즈 제공)은 정상(`pass`)** — '펀딩/후원/공동구매' 단어 자체는 위반 아님.
- **`block`은 원금 보장 / 수익(이자·배당) 보장 / 확정 투자수익 / 무위험 수익을 *긍정적으로 약속*할 때만.**
- **위험 고지·부정 표현("수익 보장 안 함", "원금 손실 위험 있음")은 위반이 아니라 정상(컴플라이언스 양성 신호)** — 위반 근거로 보지 않음.
- 명시 보장은 아니나 수익을 암시하는 경우("높은 수익률 기대" 등)는 `review`.

RAG는 **국가법령정보센터 조문 단위 인덱스**(9개 법령 1,719개 청크, MiniLM 임베딩 384차원, ChromaDB `PersistentClient(rag_db/law)` 컬렉션 `law_articles`)를 사용합니다. 인덱스가 없으면 기존 9개 법령 **설명 단위**(EphemeralClient) fallback으로 자동 동작 — 검색 정확도만 낮아지고 API 동작은 동일합니다. 인덱스 재빌드는 `scripts/build_law_index.py` → `scripts/embed_law_index.py` 참고(README/results_law.md). 필터 테스트 결과는 `results_law_test.md`.

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

**응답** (block 예시)
```json
{
  "violation": true,
  "verdict":   "block",
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

**응답** (review 예시 — 관리자 검토 큐)
```json
{
  "violation": false,
  "verdict":   "review",
  "details": [
    { "category": "과대광고 소지", "law": "식품위생법", "reason": "'다음날 개운한' 표현이 숙취 해소를 암시할 소지", "article": null }
  ],
  "recommendation": "관리자 검토가 필요합니다."
}
```

**응답** (pass 예시)
```json
{ "violation": false, "verdict": "pass", "details": [], "recommendation": "법적 문제가 없습니다." }
```

| 응답 필드 | 설명 |
|----------|------|
| `verdict` | `block` / `pass` / `review` — **`review`는 자동 차단·통과 없이 관리자 검토 큐로** |
| `violation` | 하위호환 bool. `verdict=="block"`일 때만 `true` |
| `details[]` | 위반/검토 사유. `pass`면 빈 배열 |

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

양조장용 인사이트 대시보드. 통계 집계 + 트렌드 예측 + 사용자 군집 + 선호 분포 + Gemini 자연어 리포트.
**데이터 소스**: DB 연결 시 `user_taste_history`/`user_profiles`/`_fundings`, 미연결 시 인메모리 샘플 fallback (`data_source` 필드로 구분).

```bash
curl "http://localhost:8000/api/insight?period=week"
```

| 쿼리 파라미터 | 값 | 기본값 | 설명 |
|---------------|-----|--------|------|
| period | `day` \| `week` \| `month` | `week` | 집계 기간 |

**응답**
```json
{
  "period": "week",
  "summary": "최근 320건의 리뷰(샘플 데이터)가 있으며, 평균 평점은 3.0점입니다. ...",
  "statistics": {
    "total_reviews": 320,
    "avg_rating": 3.0,
    "top_drinks": [{ "name": "...", "count": 12, "avg_rating": 3.5 }],
    "taste_distribution": { "sweetness": 5.2, "body": 5.0, "...": 0.0 },
    "funding_top": [{ "funding_id": "f1", "name": "...", "brewery": "...", "region": "...", "registered_at": "..." }],
    "data_source": "memory"
  },
  "predictions": { "trend": "stable", "predicted_growth": 0.0, "next_period_prediction": 11, "current_average": 10 },
  "clusters": [
    { "cluster_id": 0, "name": "단맛 선호형", "description": "...", "user_count": 30, "percentage": 25.0, "data_source": "memory" }
  ],
  "ai_report": "이번 주는 산미 높은 막걸리 선호도가 증가했습니다. ...",
  "data_source": "memory",
  "preferences": {
    "profile_count": 120,
    "bti4_distribution": [{ "key": "SHMU", "count": 13 }],
    "bti5_distribution": [{ "key": "SHMUH", "count": 7 }],
    "axis_preference_avg": { "sweetness": 5.0, "body": 5.0, "...": 5.0 },
    "food_pairing_top": [{ "key": "치즈", "count": 54 }],
    "aroma_distribution": [{ "key": "꽃향", "count": 41 }],
    "fruit_distribution": [{ "key": "망고", "count": 30 }],
    "data_source": "memory"
  }
}
```

| 응답 필드 | 설명 |
|-----------|------|
| `statistics.top_drinks` | 인기 전통주 순위(리뷰 수·평균평점) |
| `statistics.taste_distribution` | 리뷰 기반 8축 평균 |
| `statistics.funding_top` | 최근 등록 펀딩 전통주 (최대 10) |
| `predictions` | 지수평활 트렌드(`increasing`/`stable`/`decreasing`) + 성장률 |
| `clusters` | 사용자 취향 군집. DB 모드는 BTI 앞 2글자 기반, 메모리 모드는 8축 k-means |
| `ai_report` | Gemini 자연어 리포트 (키 없으면 안내 문구) |
| `data_source` | `"db"` = 실제 데이터, `"memory"` = 샘플 fallback |
| `preferences` | **선호 분포 인사이트** — DB `user_profiles` 또는 샘플 프로필 기반 |
| `preferences.bti4_distribution` / `bti5_distribution` | BTI 4글자(16종)·5글자(32종) 분포 (count 내림차순) |
| `preferences.axis_preference_avg` | 프로필 기반 8축 선호 평균 |
| `preferences.food_pairing_top` | 음식 페어링(q24) 빈도 상위 5 |
| `preferences.aroma_distribution` / `fruit_distribution` | 관심 향(q25)·선호 과일(q23) 분포 |

> `preferences`는 DB의 `user_profiles`(bti_code·preferred_food_pairing·preferred_aroma·preferred_fruit·taste_vector)에서 집계하며, DB 미연결 시 결정적 샘플 프로필 120건으로 데모됩니다. `data_source`로 출처를 구분하세요.

> 양조장 제품 기획용 인사이트는 이 메모리 샘플을 실데이터로 사용하지 않습니다. 백엔드가 게시물·댓글·성공 펀딩·BTI 관심 데이터를 비식별 집계해 전달하는 별도 계약 초안은 `docs/brewery-insight-aggregation-contract.md`를 참고하세요. 백엔드 계약 확정 전 AI 서버는 서비스 DB 테이블을 추측해 직접 JOIN하지 않습니다.

---

## 17. POST `/api/chat`

전통주 추천, 제품 설명, 비교, 안주 추천과 직전 추천 제품에 대한 후속 질문을 하나의 엔드포인트에서 처리합니다.
제품명과 양조장명은 실제 `app.state.recommender` 추천 풀에 있는 데이터만 사용합니다.
선택된 실제 제품 목록을 바꾸지 않은 상태에서 Gemini가 본문을 자연스럽게 큐레이션하고, 질문·본문·추천 제품에 관련된 후속 질문 2~3개를 생성합니다. Gemini 본문에 실제 선택 제품명이 하나도 없거나 호출이 실패하면 카탈로그 기반 템플릿으로 폴백합니다. 후속 질문 생성 실패 시에만 고정 fallback을 사용합니다.

서버는 대화 세션을 저장하지 않는 **무상태(stateless)** 구조입니다. 멀티턴 질문을 처리하려면 클라이언트가 이전 메시지와 직전 assistant 응답의 `referenced_drinks`를 매 요청의 `history`에 다시 보내야 합니다.

**요청**
```json
{
  "message": "그중 낮은 도수는?",
  "user_id": null,
  "history": [
    {
      "role": "assistant",
      "content": "테스트 생막걸리와 테스트 저도주를 추천합니다.",
      "referenced_drinks": [
        {"name": "테스트 생막걸리"},
        {"name": "테스트 저도주"}
      ]
    }
  ]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| message | string | Y | 사용자 질문 |
| user_id | string | N | 있으면 실제 taste history 또는 survey profile을 개인화에 사용 |
| history | array | N, 기본 `[]` | 이전 대화 기록. 각 원소는 자유 형식 object이며 `role`, `content` 또는 `message`, assistant 응답의 `referenced_drinks`를 전달해야 안정적으로 후속 제품 맥락을 복원 |

**응답 예시 — `tests/test_chat.py`의 실제 계약 fixture 기준**
```json
{
  "response": "사용자 취향 데이터가 없어 일반 추천으로 안내드립니다. 앞서 언급한 제품 중 도수가 가장 낮은 술은 테스트 저도주(3.0도)입니다.",
  "context": "traditional_korean_alcohol",
  "suggested_questions": ["테스트 저도주의 안주는?", "도수를 비교해 주세요."],
  "referenced_drinks": [
    {
      "id": "d2",
      "name": "테스트 저도주",
      "brewery": "견본양조",
      "abv": 3.0,
      "region": "서울",
      "features": "가벼운 안주와 잘 어울린다."
    }
  ],
  "next_actions": ["테스트 저도주의 안주는?", "도수를 비교해 주세요."],
  "intent": "lowest_abv",
  "personalization_source": "general"
}
```

기존 `response`, `context`, `suggested_questions` 필드는 유지됩니다. 추가 필드는 optional입니다.
`personalization_source`는 `taste_history`, `survey_profile`, `general` 중 하나이며, `general`이면 답변에 일반 추천임을 명시합니다.

| `intent` | 의미 |
|---|---|
| `recommend_drinks` | 일반·개인화 전통주 추천 |
| `food_pairing` | 안주·음식 페어링 |
| `drink_explanation` | 실제 카탈로그 제품 설명 |
| `compare_drinks` | 직전 또는 직접 언급 제품 비교 |
| `lowest_abv` | 직전 제품 중 최저 도수 |
| `out_of_scope` | 전통주와 무관한 질문 |

전통주 무관 질문은 HTTP 200으로 `context="out_of_scope"`, `intent="out_of_scope"`를 반환합니다.

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
| session_id | string | N | 현재 요청 모델 호환 필드일 뿐 서버에서 저장·사용하지 않음 |

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

`/api/chat/stream`은 이번 실제 카탈로그 제한·개인화 큐레이션 통합 대상이 아닙니다. 멀티턴 맥락 유지가 필요하면 `/api/chat`과 `history`를 사용합니다.

**에러**
- 503: `GEMINI_API_KEY` 미설정

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
`taste_input` 미입력 시 Gemini가 자동으로 맛벡터 생성을 시도하고, 실패하면 모든 축 `5.0`인 fallback 벡터를 사용합니다.
이 라우트는 현재 Pydantic 요청 모델을 직접 받지 않고 raw JSON을 읽은 뒤 필수값을 검증하여 `FundingRegisterRequest`를 구성합니다.

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
| brewery | string | Y | 양조장 이름. 빈 문자열 불가 |
| brewery_user_id | string | Y | 양조장/기획자 ID. 빈 문자열 불가 |
| region | string | N | 생산 지역 |
| abv | float | Y | 도수 (0~100) |
| main_ingredient | string | N | 주재료 |
| description | string | N | 전통주 설명 |
| taste_input | object | N | 전달된 축은 float 변환, 누락 축은 `5.0`. 없으면 Gemini 생성 후 실패 시 전체 `5.0` fallback |

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
- 400: `funding_id`, `name`, `brewery`, `brewery_user_id`, `abv` 누락
- 400: `abv`가 숫자가 아니거나 0~100 범위 밖

`source`는 `direct_input`, `gemini`, `fallback` 중 하나입니다.

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

입력 구동 프롬프트 빌더(`build_image_prompt`)가 **결정적으로** 영문 프롬프트를 조립한 후
`gemini-2.5-flash-image` 모델로 이미지를 직접 생성. (과거의 LLM 프롬프트 생성 방식 대체)
Gemini 실패 시 `HUGGINGFACE_TOKEN`이 있으면 Stable Diffusion으로 fallback.

**프롬프트 구성** — `[SUBJECT][COLOR][TEXTURE][PROPS][BACKGROUND][LIGHTING][STYLE]` 7개 섹션으로 조립:
- `taste_vector` → 시각 언어 (단맛↑ 골든톤 / 탄산↑ 기포 / 바디↑ 점성·우윳빛 / 산미↑ 신선한 하이라이트)
- `flavor_tags`·재료 → 소품·가니시, `region` → 배경 분위기
- 구도/조명/스타일은 `name`(또는 `seed`) 해시로 프리셋을 회전 → 술마다 다른 결과, 같은 입력은 재현

**요청**
```json
{
  "name":        "탄산 톡톡 딸기 요거트",
  "description": "상큼 달달한 저도수 스파클링",
  "flavor_tags": ["달콤한", "청량한", "딸기"],
  "region":      "충청남도 논산",
  "main_ingredient": "쌀",
  "sub_ingredients": ["논산 딸기"],
  "concept": "봄 소풍을 위한 저도수 스파클링",
  "taste_vector": {
    "sweetness": 8.5, "body": 3.0, "carbonation": 8.0, "flavor": 6.0,
    "alcohol": 4.0, "acidity": 6.5, "aroma_intensity": 6.0, "finish": 4.0
  },
  "seed": 12345
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| name | string | Y | 전통주 이름 |
| description | string | Y | 전통주 설명 |
| flavor_tags | string[] | N | 맛 태그 → 소품/가니시 |
| region | string | N | 지역 → 배경 분위기 |
| main_ingredient | string | N | 메인재료 → 이미지 소품 |
| sub_ingredients | string[] | N | 서브재료 → 이미지 소품 |
| concept | string | N | 프로젝트 컨셉 → 피사체·분위기 |
| taste_vector | object(8축, float) | N | 8축 맛벡터 → 색·질감 시각화. 미전달 시 중립(5) 처리 |
| seed | int | N | 구도/조명/스타일 프리셋 변주 제어. 미전달 시 `name+region` 해시 사용(재현 가능) |

**응답 — 이미지 생성 성공**
```json
{
  "status":      "success",
  "image_base64": "iVBORw0KGgoAAAANS...",
  "mime_type":   "image/png",
  "model_used":  "gemini-2.5-flash-image",
  "prompt_used": "[SUBJECT] A bottle and a slender clear glass of Korean traditional alcohol '탄산 톡톡 딸기 요거트' ...\n[COLOR] deep golden-amber, honeyed and glistening, with bright fresh dewy highlights\n[TEXTURE] light thin body, clear and translucent, lively rising bubbles ...\n[PROPS] garnished with fresh strawberries ...\n[BACKGROUND] ...\n[LIGHTING] ...\n[STYLE] ...",
  "message":     "Gemini gemini-2.5-flash-image로 이미지 생성 완료"
}
```

> **반환은 base64 PNG 문자열**입니다. 이미지 파일 저장·S3 업로드·CDN URL 발급은 **백엔드 몫**입니다(AI 서버는 바이너리를 직접 저장하지 않음). `image_base64`를 디코드해 저장 후 URL을 발급하세요.

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

재료명을 입력하면 생산 지역 목록을 반환. **Gemini 호출 없음 (즉시 응답)**.

조회 순서:
1. `data/ingredient_region_map.json` — `scripts/collect_local_products.py`가 농사로 지역특산물 OpenAPI(`localSpcprd/localSpcprdLst`)에서 수집한 매핑
2. `app/recipe.py`의 하드코딩 fallback 매핑

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
  "regions":      ["경상남도 의령군", "전북특별자치도 고창군", "전북특별자치도 남원시"],
  "found":        true,
  "data_source":  "nongsaro_api"
}
```

**응답 — 매핑 없음**
```json
{
  "ingredient":  "통밀",
  "regions":     [],
  "found":       false,
  "data_source": "unavailable"
}
```

| 필드 | 설명 |
|------|------|
| `regions` | 생산 지역 배열. 매핑 없으면 빈 배열 `[]` |
| `found` | `true` = 1개 이상 지역 매핑 성공 |
| `data_source` | `"nongsaro_api"` = `data/ingredient_region_map.json` 매칭, `"manual"` = 하드코딩 fallback, `"unavailable"` = 매핑 없음 |

> 서브재료 공식 요청은 사용자가 선택한 `region`을 별도로 전달합니다. 지역 목록 첫 항목을 서버가 임의 선택하지 않습니다.
> 원본 농사로 수집 레코드는 `data/local_products.json`에 보관되고, API는 그 결과를 재가공한 `data/ingredient_region_map.json`을 읽습니다. 코드에서는 `"경상남도 > 의령군"` 형태를 `"경상남도 의령군"`처럼 정규화해 반환합니다.

### 프론트 2단계 연동

1. 메인 재료 입력 후 `GET /api/recipe/ingredient-region?ingredient=사과`를 호출합니다.
2. 응답의 `regions`를 지역 선택 UI에 표시합니다.
3. 사용자가 선택한 지역과 원래 메인 재료를 분리해 `POST /api/recipe/suggest-sub-ingredients`로 전달합니다.

```json
{
  "main_ingredient": "사과",
  "region": "청주시"
}
```

`"청주 사과"`처럼 지역과 재료를 결합해 보내는 것은 공식 계약이 아닙니다. `region` 누락 시 서버는 `"전국"`을 임의 적용하지 않고 `data_source="unavailable"`과 빈 후보 목록을 반환합니다.

**지원 재료 예시**

| 재료 | 추론 지역 (복수 가능) |
|------|---------------------|
| 쌀 | 경상남도 의령군, 전북특별자치도 고창군, 전북특별자치도 남원시, 충청남도 논산시, 충청북도 청주시, 강원특별자치도 철원군 등 |
| 사과 | 경상북도 청송, 충청북도 충주, 경상남도 거창 |
| 딸기 | 충청남도 논산, 경상남도 진주 |
| 감귤, 한라봉 | 제주도 |
| 잣 | 경기도 가평 |
| 인삼, 홍삼 | 충청남도 금산, 경상북도 영주 |
| 녹차 | 전라남도 보성 |
| 포도 | 경상북도 영천, 충청북도 영동 |

---

## 27. POST `/api/brewery/verify-ocr` ✦ Gemini

양조장 인증/신원 서류 파일을 Gemini Vision으로 분석하여 서류 종류 판별 및 필드 추출.
지원 서류는 `app/ocr.py`의 `SUPPORTED_DOC_TYPES` 레지스트리에서 관리합니다.
OCR 결과는 관리자 검토 자료이며 자동 승인에 사용하지 않습니다.

**현재 인식 가능한 서류 7종**
1. 사업자등록증
2. 신분증
3. 통신판매업신고증
4. 주류통신판매승인서
5. 전통주제조면허증
6. 주류제조면허증
7. 식품제조가공업영업신고증

**요청** `multipart/form-data`

```bash
curl -X POST "http://43.201.97.229:8000/api/brewery/verify-ocr" \
  -F "file=@business-license.png;type=image/png" \
  -F "originalName=business-license.png" \
  -F "mimeType=image/png"
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| file | file | 조건부 | — | 공식 백엔드 필드 미확정. `businessLicense`와 임시 호환 |
| businessLicense | file | 조건부 | — | `file` 임시 호환 필드 |
| mimeType | string | N | — | upload content type이 없을 때 검증용 |
| mime_type | string | N | — | `mimeType` snake_case 호환 alias |
| documentUrl / documentKey / originalName | string | N | — | 현재 OCR 및 DB 저장에 사용하지 않음 |
| document_url / document_key / original_name | string | N | — | 위 camelCase 필드의 snake_case 호환 alias. 현재 처리·저장에는 사용하지 않음 |

PNG, JPEG, PDF magic bytes와 MIME 타입을 함께 검증하며 파일 크기 상한은 10MB입니다.
PDF는 코드 경로만 지원하며 실제 Gemini 라이브 호출은 미검증입니다.

**응답 — OCR 완료**
```json
{
  "status": "COMPLETED",
  "ocrSucceeded": true,
  "verified": false,
  "documentAssessment": "REVIEW_REQUIRED",
  "summary": {
    "businessNumber": "214-88-12345",
    "breweryName": "테스트양조장",
    "representativeName": "김테스트",
    "address": "서울특별시 테스트구",
    "licenseType": "사업자등록증",
    "manualReviewOnly": true,
    "reviewPolicy": "OCR_RESULT_IS_FOR_ADMIN_REVIEW_ONLY"
  },
  "rawText": "OCR로 읽은 원문",
  "warnings": []
}
```

**응답 — OCR 업무 실패**
```json
{
  "status": "FAILED",
  "ocrSucceeded": false,
  "verified": false,
  "documentAssessment": "MANUAL_REVIEW",
  "summary": {
    "reason": "UNSUPPORTED_FILE_TYPE",
    "manualReviewOnly": true,
    "reviewPolicy": "OCR_RESULT_IS_FOR_ADMIN_REVIEW_ONLY"
  },
  "error": "PNG, JPEG, PDF 파일만 지원합니다.",
  "warnings": ["관리자 수동 검토가 필요합니다."]
}
```

인증 신청 비차단 정책을 위해 모든 OCR 업무 결과는 HTTP 200이며 `body.status`로 완료·실패를 구분합니다.
실패 reason은 `NO_FILE`, `EMPTY_FILE`, `FILE_TOO_LARGE`, `UNSUPPORTED_FILE_TYPE`, `OCR_PROCESSING_FAILED`입니다.
사업자등록번호 체크섬 실패와 필드 누락은 반려가 아니라 `warnings`에만 추가됩니다.
`documentUrl`, `documentKey`, `originalName`은 현재 처리·저장에 사용되지 않으며, 원본 bytes/base64는 응답이나 일반 로그에 기록하지 않습니다. `rawText`는 응답에는 포함되지만 일반 로그에는 남기지 않습니다.
`app.models.BreweryOCRRequest`의 기존 base64 모델 정의는 import 호환을 위해 남아 있지만 현재 `/api/brewery/verify-ocr` 라우트에서는 사용하지 않습니다.

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
4. POST /api/law/filter                       ← 광고 문구 법률 검토 (verdict=pass 통과 / block 차단 / review 관리자검토)
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

---

## 변경 이력

### 2026-06-14
- **`POST /api/brewery/verify-ocr` JSON/base64 → multipart 전환**: `file`/`businessLicense` 임시 호환, document metadata와 MIME의 camelCase/snake_case alias 수신, PNG·JPEG·PDF magic bytes 및 MIME 검증, 10MB 상한. `python-multipart` 의존성 추가.
- **OCR 관리자 검토 정책**: OCR 완료·실패 모두 자동 승인하지 않으며 `verified=false`. 인증 신청 비차단을 위해 업무 실패도 HTTP 200 + `body.status="FAILED"`로 반환.
- **`POST /api/recipe/suggest-sub-ingredients` Gemini 보조 선별**: 실제 지역 후보 안에서만 궁합 선별하고 실패 시 기존 후보로 폴백. `SubIngredientsResponse` 계약은 유지.
- **`GET /api/recipe/ingredient-region` 2단계 흐름 명시**: 메인 재료로 복수 지역 조회 후 사용자 선택 지역을 서브재료 API에 별도 전달.
- **`POST /api/chat` 통합 큐레이션**: 실제 카탈로그 제품만 선택한 후 `_build_answer_curated`로 본문을 생성하고 실패 시 템플릿 폴백. 서버 무상태 멀티턴, `history.referenced_drinks`, `next_actions`, `intent`, `personalization_source`, `out_of_scope` 계약 명시.
- **`POST /api/chat/stream` 범위 명시**: 통합 큐레이션 대상이 아니며 `session_id`는 현재 사용되지 않음.

### 2026-06-01
- **`/api/law/filter` 3등급 판정(`verdict` block/pass/review) 반영** — `review`는 자동 차단·통과 없이 관리자 검토 큐로. `violation`은 `block`일 때만 `true`(하위호환). 모든 콘텐츠를 Gemini 1회 검토(무검토 통과 경로 제거), 실패 시 키워드 fallback.
- **법률 RAG**: 국가법령정보센터 조문 단위 인덱스(9개 법령 1,719 청크, MiniLM 384d, ChromaDB `PersistentClient(rag_db/law)`/`law_articles`), 인덱스 없으면 9개 설명 단위 EphemeralClient fallback.
- **펀딩 판정 정밀화**: 리워드형 펀딩은 정상(pass), 원금·수익 보장 등 *긍정 약속*만 block, 위험 고지·부정 표현은 정상 신호로 처리(review/pass). (테스트: `results_law_test.md` — 안전율 100%·위험 FN 0)
- `.env.example` 추가(키 목록 템플릿), `LAW_EMBED_MODEL`/`LAW_USER_AGENT`/`LAW_REFERER` 환경변수 문서화.

### 2026-05-31
- 농사로 지역특산물 API 수집 결과(`data/local_products.json`, `data/ingredient_region_map.json`) 기반 재료→지역 매핑과 하드코딩 fallback 구조를 문서화.
- `/api/image/generate`의 `build_image_prompt()` 기반 프롬프트, `taste_vector`/`seed` 입력, base64 PNG 응답, S3 업로드 역할 분리를 반영.
- `/api/brewery/verify-ocr`를 `SUPPORTED_DOC_TYPES` 레지스트리 기준 7종 서류로 갱신하고 더미 OCR 검증 결과와 한계를 정리.
- `/api/survey/convert` 기준 BTI는 현재 5글자(`bti_code`) 응답이며, BTI 도수 H/L 임계값은 alcohol 5.5로 정리. 4글자 BTI 논의는 정적 웹 설문(`web/survey/index.html`)의 `bti4` 참고 사항으로만 유지.
