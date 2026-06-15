# AI 파트 최종 QA (results_final_qa.md)

프로젝트 마지막 점검. **실제 호출/코드로 확인, 추측·조작 없음, 키 값 미출력.** 동작+입력처리+응답일관성+UX.
수정 원칙: 명백한 1줄 버그·가드만 즉시 수정, 설계 판단·여러 줄은 **❓확인 필요**로 보류.

- 서버: `uvicorn app.main:app`(로컬), gemini=on / law_key=on / **db=false(메모리 fallback)** / data=207.
- Gemini 호출은 기능당 최소화(법률 3등급·이미지·OCR·챗 각 1회 수준).

---

## 기능별 점검 결과표

| 영역 | 상태 | 핵심 결과 |
|------|:----:|-----------|
| [1] survey/convert·taste/profile | ✅ 정상 / ❓일부 | 25문항→8축·bti·캐릭터·선호 정상, 견고성 422. **도수축 4/5글자·캐릭터vs라벨 모순=❓** |
| [2] recommend | ✅ 정상 | 400/422 적절, match_reason·similarity(0~1) 정상, pool 가드 동작, 빈 풀=빈배열 |
| [3] law/filter·law/info | ✅ 정상 | block/pass/review verdict 항상 존재, 빈/긴/특수문자 무크래시, fallback verdict 채움(코드확인) |
| [4] image/generate | ✅ 정상 | taste_vector 없음=중립 success, base64·model_used·prompt_used 포함 |
| [5] recipe/register·ingredient-region | ✅ 수정함 | register/data_source 정상. **빈 ingredient 오매칭 버그 수정** |
| [6] brewery/verify-ocr | ✅ 정상 | 무관 이미지→is_valid=False, 잘못된 base64→graceful, 빈→400 |
| [7] chat·chat/stream | ✅ 정상 | 관련 답변+추천질문3, 비관련/빈메시지→out_of_scope(Gemini 미호출), stream SSE 200 |
| [8] insight | ✅ 정상 | statistics·predictions·clusters·preferences 전부, 메모리 fallback |

---

## ✅ 수정함 (이번 세션)

### recipe.py — 빈/공백 ingredient substring 오매칭 버그
- **현상(버그)**: `GET /api/recipe/ingredient-region?ingredient=`(빈값) → `found=True`, **엉뚱한 쌀 생산지 6곳 반환**. 원인: `_match_nongsaro_regions`·`get_region_from_ingredient`의 `ingredient in name`/`key in ingredient` 매칭에서 빈 문자열이 **모든 항목의 substring**이라 전 항목과 오매칭.
- **수정(1줄 가드 ×2)**: 두 함수 상단에 `if not ingredient(.strip()): return []` 추가. (빈값만 차단, 유효 입력 로직 불변)
- **재검증(서버 재기동 실호출)**:
  | ingredient | 전 | 후 |
  |---|---|---|
  | `''`(빈) | found=True, 쌀 6곳(오류) | **found=False, n=0** ✅ |
  | `'   '`(공백) | (동일 오류) | **found=False, n=0** ✅ |
  | `쌀` | nongsaro 6곳 | **nongsaro 6곳(불변)** ✅ |
  | `감귤` | manual 1곳 | **manual 1곳(불변)** ✅ |
  | `없는재료xyz` | found=False | **found=False(불변)** ✅ |
- 발표 영향: **낮음**(빈 입력은 정상 플로우서 드묾) / 심각도 하 / 기존 동작 무회귀.

> 참고: `requirements.txt`(google-genai)·`/api/recommend` pool 가드는 직전 커밋(9c4a8fc)에 이미 반영됨. 이번 재점검에서 pool 가드 재동작 확인(garbage→400, 유효 pool→정상, 빈 풀→[]).

---

## ❓ 확인 필요 (설계 판단 — 자동 수정 안 함)

### Q1. ★ bti_code 도수축 — 4글자 vs 5글자 (+ 캐릭터/라벨 모순) — 발표 영향 있음
- **현황**: `/api/survey/convert`가 **`bti_code='SHFUH'`(5글자)** 반환. 5번째 글자=도수 H/L(임계 **5.5**). 그러나 프로젝트 결정은 **4글자(도수 분류축 제외)**. → **불일치.**
- **추가 모순(같은 응답 내)**: `character_name="탄산 톡톡 딸기 요거트 **(고도수)**"`(5번째 H 기반) vs `alcohol_label="**저도수**(8도 이하)"`(임계 **9.0** 기반). **고도수↔저도수 정면 모순** — 화면에 그대로 노출되면 사용자 혼란. 원인: 도수 임계가 코드(5.5)와 라벨(9.0)에서 서로 다름.
- **옵션 A (4글자 확정)**: `bti_code`를 앞 4글자로, 도수는 `alcohol_label`로만 표기. → `BTI_TYPE_MAPPING`·캐릭터명에서 (고/저도수) 분리 필요(여러 줄·응답 의미 변경). 정적 웹 설문(`bti4`)과 일치.
- **옵션 B (5글자 유지)**: 구조 유지하되 `alcohol_label`/캐릭터의 도수 임계를 **5.5로 통일**해 모순만 제거.
- **권고**: 발표 직전 응답구조/캐릭터 매핑 대수술은 위험 → 우선 **모순 제거(B)** 가 안전. 4/5글자 최종 확정은 사용자 결정. (`alcohol_score`/`alcohol_preference` 별도 필드는 **없음** — alcohol은 `taste_vector` 내부 + `alcohol_label` 문자열 + `preferred_abv`로만 제공.)

### Q2. survey q24/q25 항목 도메인(1~5) 미검증 — 발표 영향 없음
- **현황**: `q24=[99]`·`q25=[99]` 같은 도메인밖 정수도 200(변환기가 unknown 매핑·skip으로 graceful, **크래시 아님**). 응답에 "unknown"이 노출되진 않음(확인).
- **옵션 A**: pydantic `field_validator`로 항목 1~5 검증(여러 줄). **옵션 B**: 현행 유지.
- **권고**: 무해·후순위. 자동 수정 안 함(여러 줄).

### Q3. 에러 응답 형식 불일치 [횡단10] — 발표 영향 없음
- **현황**: 검증 실패 422는 `{"detail":[...array...]}`, 비즈니스 가드 400은 `{"detail":{"status","message"}}`(recommend 상단·funding) **또는** `{"detail":"문자열"}`(taste/profile 404, recommend 내부 user_id). 같은 엔드포인트 내에서도 dict/string 혼재.
- **옵션 A**: 공통 예외 핸들러로 `{status,message}` 통일. **옵션 B**: 현행 유지.
- **권고**: 프론트가 이미 맞춰져 있으면 유지, 통일은 발표 후. 자동 수정 안 함(여러 줄·회귀 위험).

### Q4. OCR/이미지 실패 시 내부 메시지 노출 [횡단11] — 발표 영향 낮음
- **현황**: 잘못된 base64 → `{status:"error", message: <내부 예외문자열>}`(200, graceful). 이미지 실패도 `status:"error", message:str(e)`.
- **옵션 A**: 사용자용 일반 메시지로 치환. **옵션 B**: 현행 유지(크래시는 아님).
- **권고**: 경미·후순위.

---

## 횡단 점검 결과

| # | 항목 | 결과 |
|---|------|------|
| 9 | 입력검증 일관성 | **비정상 입력에 500/크래시 0건** — 전부 422(검증)/400(가드)/graceful 200. (빈 ingredient는 500은 아니나 오데이터 반환이었음 → 수정함) |
| 10 | 응답 일관성 | ⚠️ 에러 detail 형식 혼재(dict/string/array) → Q3 제안 |
| 11 | UX | ⚠️ bti 캐릭터(고도수)↔alcohol_label(저도수) 모순=Q1 / status=error 내부메시지=Q4 / **"unknown"·깨진문자열·빈 핵심필드 노출은 없음**(survey 캐릭터·요약 자연스러움 확인) |
| 12 | 외부호출 안전 | 신규 코드(pool·빈값 가드)는 외부호출 없음. 기존 Gemini 호출은 try/except+timeout 보유(law `GEMINI_TIMEOUT_SEC`, image/chat try/except, 429→503 매핑) |

---

## 발표 영향·심각도 요약

| 항목 | 발표 영향 | 심각도 | 조치 |
|------|:--------:|:------:|------|
| 빈 ingredient 오매칭 | 낮음 | 하 | ✅ 수정함 |
| **bti 4/5글자 + 캐릭터·라벨 도수 모순** | **있음** | **중** | ❓확인 필요(Q1) |
| q24/q25 도메인 미검증 | 없음 | 하 | ❓확인 필요(Q2) |
| 에러 응답 형식 혼재 | 없음 | 하 | ❓확인 필요(Q3) |
| OCR/이미지 내부메시지 노출 | 낮음 | 하 | ❓확인 필요(Q4) |
| 법률 경계 verdict 변동(Gemini) | 없음 | 하 | 관찰(정상·안전) |

### 종합
- **발표 차단 이슈 없음. 비정상 입력에 서버 크래시(500) 0건.** 8개 기능 영역 + stream 전부 실호출 정상.
- 명백한 버그 1건(빈 ingredient)만 1줄 가드로 수정·무회귀 검증.
- **유일하게 화면 영향 가능한 것은 Q1(도수 고/저 모순)** — 발표 전 사용자 결정 권장(최소 모순 제거).
- 나머지(q24 검증·에러형식 통일·내부메시지)는 발표 영향 없음, 발표 후 처리 가능.

### 이번에 수정한 파일 (미커밋 — 커밋 여부 지시 대기)
1. **`app/recipe.py`** — `_match_nongsaro_regions`·`get_region_from_ingredient`에 빈값 가드 1줄씩(빈/공백 ingredient substring 오매칭 차단). 실호출 무회귀 검증.

*(점검용 서버 종료, 임시파일 정리 완료.)*
