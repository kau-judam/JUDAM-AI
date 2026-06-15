# 프로젝트 최종 마감 점검 (results_final_check.md)

발표/배포 전 사각지대 점검. **실제 코드/실호출로 확인, 추측·조작 없음, 키 값 미출력.**
원칙: **명백한 1줄 버그만 수정, 나머지 제안.** Gemini 호출 최소화.

---

## 1. EC2 기동 가능성 ★최우선

### ✅ 수정함 — requirements.txt에 `google-genai` 누락 (핵심)
- 코드가 **두 종류의 google SDK**를 import:
  - `import google.generativeai`(구 SDK, 패키지 `google-generativeai`) — chat·law_client·insight·auto_pipeline·tasting_note_converter. **requirements 있음.**
  - `from google import genai` / `import google.genai`(신 SDK, 패키지 **`google-genai`**) — **ocr.py·recipe.py·image_generator.py·chat.py(스트리밍)**. **requirements에 없었음.**
- 로컬엔 둘 다 설치(구 0.8.6 / 신 1.74.0)돼 동작하나, **신규 EC2 `pip install -r requirements.txt` 시 `google-genai` 미설치 → OCR·이미지생성·레시피Gemini·챗스트리밍이 런타임 import 실패**(임포트가 함수 내부라 서버 기동 자체는 되지만 해당 기능 호출 시 에러).
- **수정**: `requirements.txt`에 `google-genai>=1.0.0` 추가(설치본 1.74.0 기준 안전한 하한).

### ✅ 그 외 의존성 — 누락 없음
- app/ 전체 import AST 스캔 결과 3rd-party: asyncpg·boto3·bs4·chromadb·dotenv·fastapi·httpx·pydantic·requests·sentence-transformers·uvicorn·google → **`google-genai` 외 전부 requirements에 존재.**

### ✅ .env.example ↔ 코드 환경변수 — 일치 (누락 없음)
- 코드가 읽는 7개: `GEMINI_API_KEY`·`DATABASE_URL`·`LAW_API_KEY`·`LAW_EMBED_MODEL`·`LAW_REFERER`·`LAW_USER_AGENT`·`HUGGINGFACE_TOKEN` → **전부 .env.example에 있음.**
- `NONGSARO_API_KEY`는 수집 스크립트 전용(app/ 미사용) — 정상. REDIS_URL/AWS_*/PORT/LOG_LEVEL은 example엔 있으나 app/ 런타임 미사용(무해).

### ⚠️ 제안 (기동엔 무관)
- **Pillow(PIL)**: `scripts/gen_dummy_docs.py`(더미 생성 dev 스크립트)만 사용. 서버 런타임 무관이라 requirements 미포함이 기동을 막진 않음. EC2에서 더미를 재생성할 일이 있으면 `pillow` 추가 권장.
- **loguru**: requirements엔 있으나 app/에서 import 안 함(불필요 의존, 무해).
- 죽은 import·기동 에러: **없음** — 서버 `/health` 200 정상 기동 확인.

---

## 2. 11주차 기능 회귀 — 실호출 전부 정상

| 기능 | 호출 | 결과 |
|------|------|------|
| survey/convert (BTI·캐릭터) | POST (user_id 저장) | ✅ 200, bti=**SHFUH**, char="탄산 톡톡 딸기 요거트(고도수)", method=rule_based |
| taste/profile | GET /api/taste/profile/demo_fc | ✅ 200, 프로필 저장·조회됨(bti=SHFUH) |
| recommend **match_reason** | POST (user_id) | ✅ 200, 3건, match_reason=**['단맛이 잘 맞아요','바디감이 비슷해요']** |
| 전통주 챗봇 /api/chat | POST | ✅ 200, context=**traditional_korean_alcohol**, 답변 생성, 추천질문 3개 |
| Gemini 429→503 | (코드 검증) | ✅ `main.py:183-188 raise_api_error`: `429`/`quota exceeded`/`resource_exhausted`→**503** 매핑 존재. recipe·law·recipe_validate가 이 핸들러 사용. (실 429는 강제 불가 → 매핑 로직으로 검증) |

→ **이번 변경(법률 few-shot 등)이 11주차 기능을 깨지 않음** 확인.

---

## 3. 하드코딩·낡은 값

### ✅ 코드(app/)는 깨끗
- app/ 전체에 **하드코딩 private IP/`localhost`/`:8000` 없음**(grep 확인).
- 코드 내 외부 URL은 전부 정상 의존: `law.go.kr`(법령 API), `api-inference.huggingface.co`(이미지 SD fallback), `koreansool.co.kr`(크롤러). → 신규 public 서버와 무관하게 동작.

### ⚠️ 제안 — 문서의 구 private IP (코드 아님)
- **`BACKEND_INTEGRATION.md`**: 전 엔드포인트 예시가 **구 private IP `http://10.0.11.241:8000`** 으로 하드코딩(9곳). 신규 public 서버 주소로 **문서 갱신 필요**(문서라 제안만, 코드 영향 없음).
- `DEPLOYMENT.md`는 `your-ec2-public-ip`·`your-domain.com` 플레이스홀더라 무해.

---

## 4. 무검증 입력 가드 (results_audit2 지적분)

### ✅ 수정함 — recommend `pool` 화이트리스트 가드
- 기존: `pool='garbage'`도 200(recommender에서 매칭 안 돼 조용히 'all'류 fallback).
- **수정**(`main.py` recommend 상단, 기존 400-가드 스타일과 동일 1줄):
  `pool not in (all/base/funding/recipe/approved)` → **400**.
- **검증(재기동 후 실호출)**: garbage→**400**, all·base→200(결과), funding·recipe·approved→200(빈 풀), 미지정(기본 all)→200. **유효 pool 회귀 없음.**

### ⚠️ 제안 — survey q24/q25 항목 도메인(1~5) 미검증
- `q24=[99]`·`q25=[99]` 같은 도메인밖 정수도 200(변환기가 `.get(...,'unknown')`으로 graceful 처리 → **크래시 아님, 조용한 오입력**).
- 항목 범위 검증은 pydantic field_validator(여러 줄)라 **1줄 초과 → 제안만.** (현재 무해하므로 우선순위 낮음.)

---

## 5. 엔드포인트 ↔ API_GUIDE 일치

- main.py + chat.py **총 27개 라우트 전부 `API_GUIDE.md`에 문서화됨**(누락 0).
- 코드엔 있는데 문서 없음: **0건.** (chat 라우터는 `/api` prefix로 마운트 → `/api/chat`·`/api/chat/stream` 문서 존재 확인.)

---

## 6. 데모 시나리오 — 끝까지 실호출 통과

**흐름 A (설문→BTI→추천→이미지):**
- survey/convert → BTI **SHFUH** ✅ → recommend(match_reason 포함) ✅ → image/generate **200, status=success, image 2.15MB, model=gemini-2.5-flash-image** ✅

**흐름 B (콘텐츠 등록→법률 3등급):**
- recipe/register(direct_input) → **200, source=direct_input** ✅
- law/filter **block**(원금보장 펀딩) ✅ / **pass**(복숭아 막걸리) ✅ / **review**(수험생 집중 막걸리, B7) ✅ — 3등급 모두 실제 반환.

→ **중간에 끊기거나 빈 응답 없음.**

**관찰(버그 아님)**: 경계 케이스 "무조건 최고의 명주"(A5)는 run에 따라 review↔block 변동(Gemini 판단 비결정성). A5의 기대값이 원래 block이라 오답 아니며, review여도 안전(관리자 큐). 3등급 메커니즘은 정상.

---

## 7. 정직한 결론 — 발견 항목 (우선순위순)

| 항목 | 발표 영향 | 심각도 | 조치 |
|------|:--------:|:------:|------|
| **requirements `google-genai` 누락** | **있음**(EC2 OCR/이미지/레시피/챗스트림) | **높음** | ✅ **수정함**(추가) |
| recommend `pool` 무검증 통과 | 거의 없음(데모 흐름엔 'all') | 중 | ✅ **수정함**(400 가드, 실호출 검증) |
| BACKEND_INTEGRATION.md 구 private IP | 있음(연동 문서 혼선) | 중 | ⚠️ 제안(문서 갱신) |
| survey q24/q25 도메인 미검증 | 없음(graceful) | 하 | ⚠️ 제안(pydantic validator) |
| Pillow 미포함 | 없음(서버 무관, dev 스크립트만) | 하 | ⚠️ 제안(필요 시) |
| 법률 경계 케이스 verdict 변동 | 없음(안전) | 하 | 관찰만(정상 동작) |

### 종합
- **발표 차단 이슈 없음.** 핵심 기동 리스크(`google-genai`)는 수정 완료 → EC2에서 `pip install -r requirements.txt`로 전 기능 설치 가능.
- 11주차 기능(챗봇·BTI·추천·match_reason·프로필) **실호출 전부 정상**, 이번 변경으로 깨진 곳 없음.
- 데모 2흐름(설문→이미지 / 등록→법률3등급) **끝까지 통과.**
- 남은 제안(문서 IP·q24 검증·Pillow)은 **발표 영향 없음**, 발표 후 처리 가능.

### 이번에 변경한 파일 (실호출 검증 완료, 미커밋)
1. **`requirements.txt`** — `google-genai>=1.0.0` 추가.
2. **`app/main.py`** — recommend `pool` 화이트리스트 400 가드 1줄(기존 가드 스타일 동일, 유효 pool 무회귀 확인).

*(점검 위해 띄운 서버는 종료, 임시파일 정리 완료. 위 2개 변경은 커밋하지 않음 — 커밋 여부는 지시 주시면 진행.)*
