# 향후 과제 (FUTURE_WORK)

지금까지 분석/점검에서 발견됐으나 **아직 적용하지 않은** 개선점 정리.
각 항목은 **왜 필요 / 현재 상태 / 적용 방법** 한 줄씩. (근거: `results_survey_analysis.md`, `results_ocr.md`, `results_audit.md`, `results_audit2.md`, `results_law*.md`)

> 코드 변경 없음 — 발표 후 우선순위에 따라 착수.

---

## 1. 설문 (술BTI)

### 1-1. 음식 보기에 '전(부침개)' 추가  ★최우선
- **왜 필요**: 실사용자 음식 자유응답 23건 중 **20건(87%)이 전/파전/김치전** — 막걸리 대표 안주가 보기에 없어 사용자가 매번 직접 입력 중.
- **현재 상태**: q24 음식 보기 = 고기·해산물·매운음식·디저트·치즈 (전 없음). `survey_converter.food_pairing_map`도 5종 고정.
- **적용 방법**: q24 보기에 '전/부침개' 추가 + `food_pairing_map`·`_FOOD_LABEL`에 항목 1줄 추가(웹 설문 `web/survey`와 동기화).

### 1-2. 단맛 축 — 과일계 / 곡물계 세분화
- **왜 필요**: memo "과일 향보다 쌀·구수한 향 선호", 향 자유응답 "고구마·밤 등 달달한 맛"·"밤" → 곡물계 단맛(밤·고구마·쌀)과 과일계 단맛(딸기·복숭아)이 한 축에 뭉쳐 구분 불가.
- **현재 상태**: sweetness 단일 축 + flavor의 U/C(과일계/곡물계)만 존재, 단맛의 결은 미구분. 밤막걸리류 수요 누락.
- **적용 방법**: 단맛에 곡물계/과일계 태그를 부여하거나 보조 축 추가 → BTI 매핑/추천 태그에 반영.

---

## 2. KNN 추천/분류

### 2-1. 실사용자 '아니오' 피드백 축적 시 KNN 학습 전환
- **왜 필요**: 경계 분석상 룰축의 29~43%가 임계 5 근처 → 고정 단일 임계의 오분류 한계. 데이터 기반 분류가 경계 케이스를 더 잘 가름.
- **현재 상태**: `survey_converter`는 `models/knn_bti_model.pkl` 없으면 **rule_based fallback**(현재 KNN 미로드). 실사용자 설문 76건은 is_match 전부 '맞음'이라 '아니오' 학습 신호가 0.
- **적용 방법**: `bti/feedback`의 `is_correct=false`·`actual_preference`를 축적 → 충분량 도달 시 `scripts/train_knn.py`로 학습 → pkl 배치하면 hybrid 자동 활성화.

---

## 3. 법률 필터

### 3-1. ko-sbert 임베딩 전환 옵션 (정확도)
- **왜 필요**: 조문 RAG 검색 정확도 향상(한국어 법률 문장 특화 임베딩이 다국어 MiniLM보다 유리).
- **현재 상태**: `app/embedder.py` 기본 `paraphrase-multilingual-MiniLM-L12-v2`(384d). 교체용 `LAW_EMBED_MODEL` 환경변수 훅은 이미 존재.
- **적용 방법**: `LAW_EMBED_MODEL=jhgan/ko-sbert-sts`(또는 KR-SBERT)로 지정 후 `scripts/embed_law_index.py` 재색인 → A/B로 정확도 비교.

### 3-2. REVIEW 큐 백엔드 연동
- **왜 필요**: 법률 판정 3등급 중 `verdict=review`(관리자 검토 필요)가 현재 응답에만 존재하고 처리 흐름이 없음.
- **현재 상태**: `law/filter`가 block/pass/review를 반환하나 review 건의 적재/관리 큐가 미연동.
- **적용 방법**: review 응답을 백엔드 관리자 큐(테이블/엔드포인트)로 전달 → 운영자 승인·반려 워크플로 연결.

---

## 4. 이미지 생성

### 4-1. 맛벡터 전달 백엔드 연동
- **왜 필요**: `image/generate`가 맛벡터(8축)를 받으면 색·질감 시각화를 더 정확히 반영 가능(이미 생성기 로직은 지원).
- **현재 상태**: AI 서버는 `taste_vector`(선택) 파라미터 수신 준비 완료. 백엔드가 아직 이 값을 전달하지 않음(미연동).
- **적용 방법**: 백엔드 펀딩/레시피 이미지 생성 호출 시 해당 항목의 8축 맛벡터를 함께 전달.

---

## 5. 안전장치

### 5-1. M1 — Gemini 실패 fallback (펀딩/승인 등록)
- **왜 필요**: `funding_register`·`approve_drink_request`의 `create_taste_vector(use_gemini=True)`가 try 안에 있어 **Gemini 실패 시 500**.
- **현재 상태**: 미적용. `image/generate`는 prompt_only fallback 보유(양호)하나 펀딩/승인은 미보호(`results_audit.md` M1).
- **적용 방법**: pipeline 호출을 try/except로 감싸 실패 시 `_create_basic_vector`(룰 기반 기본벡터)로 fallback.

### 5-2. M2 — base64 크기·형식 검증 (OCR/이미지 입력)
- **왜 필요**: 초대형·깨진 base64 입력 시 메모리 급증·디코드 오류 위험.
- **현재 상태**: 미적용. `verify-ocr`는 빈값 가드만 있고 `ocr.py _decode_base64`는 길이 상한·mime 검증 없이 디코드(`results_audit2.md` 2절에서 재확인).
- **적용 방법**: 디코드 전 길이 상한(예 ~10MB) + try/except 디코드 가드 + mime 화이트리스트(image/jpeg·png).

### 5-3. (보조) 핸들러 가드 규약화 + 조용한 오입력 차단
- **왜 필요**: 일부 핸들러(`bti/feedback`·`image/generate`)에 외부 try/except 없음. `recommend pool`·`survey q24/q25`는 잘못된 값도 조용히 200 통과.
- **현재 상태**: 현 시점 500 미발생(견고성 양호)이나 가드 부재·무검증 입력 존재(`results_audit2.md` 제안 P1·P2·P4).
- **적용 방법**: 핸들러 전체 try/except 규약 + pool 화이트리스트·q24/q25 도메인(1~5) 검증 추가.

---

## 6. 인프라

### 6-1. 인메모리 상태 DB 영속화
- **왜 필요**: 서버 재시작/오토스케일 시 데이터 소실 → 발표·운영 리스크.
- **현재 상태**: `_user_profiles`·`_fundings`(부분 DB)·`_recipes`·`_drink_requests`가 인메모리. 펀딩/프로필만 일부 DB upsert, 레시피·요청은 메모리 전용(`results_audit.md` H1).
- **적용 방법**: 레시피·등록요청도 DB upsert/조회 일원화 → 재시작 내성 확보. (발표 중엔 단일 인스턴스 고정·재시작 금지)

### 6-2. EC2 법률 인덱스 배포 + LAW API IP 등록
- **왜 필요**: 실시간 조문 조회와 RAG 검색을 서버 환경에서 안정 동작시키기 위함.
- **현재 상태**: ChromaDB `EphemeralClient`라 재시작마다 재적재(영속성 없음, `results_audit.md` L3). LAW API(law.go.kr)는 호출 서버 IP 등록 필요 → 현재 미등록으로 실시간 조문 비활성, 내장 RAG fallback 동작(H2).
- **적용 방법**: EC2 고정 IP/도메인을 law.go.kr OPEN API에 등록 + Chroma 영속 디렉터리(또는 사전색인 배포)로 전환.

---

## 우선순위 요약
| 순위 | 항목 | 근거 |
|:----:|------|------|
| 1 | 1-1 음식 보기 '전' 추가 | 실사용자 87% 자유입력 |
| 2 | 6-2 LAW API IP 등록 / 6-1 영속화 | 운영 안정성(H1·H2) |
| 3 | 5-1 M1 · 5-2 M2 안전장치 | 장애 내성 |
| 4 | 1-2 단맛 세분화 · 2-1 KNN 전환 | 분류 정확도(데이터 축적 선행) |
| 5 | 3-1 ko-sbert · 3-2 REVIEW 큐 · 4-1 이미지 연동 | 정확도/연동 고도화 |
