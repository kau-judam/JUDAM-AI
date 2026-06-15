# 서비스 구조 점검 (results_audit.md)

발표/연동 전 점검. 실제 코드(`app/`)를 읽고 작성. 심각도 [상/중/하].
**원칙:** 명백한 1줄 버그만 수정, 큰 변경은 제안만. 라이브 호출 최소화.

## 적용한 코드 수정 (1건, 안전)
- **`app/main.py` `/api/recommend`** — `except Exception` 앞에 `except HTTPException: raise` 추가.
  내부에서 던진 입력검증 400(저장된 user_id 프로필 없음 등)이 500으로 둔갑하던 것을 정정. 성공 경로 영향 없음.

---

## [상] 발표/연동 중 터질 수 있음

| # | 위치 | 왜 문제 | 수정안(제안) |
|---|------|---------|-------------|
| H1 | `main.py` `_drink_requests`(~908) · `_fundings`(~1059) · `_recipes`(~1235) · `_user_profiles` | **서버 재시작/오토스케일 시 전소.** 펀딩·프로필은 DB upsert 시도(부분 영속), drink_requests·recipes는 메모리 전용 → 재시작 시 사라짐 | 발표 중 단일 인스턴스 고정·재시작 금지. 중기: 등록요청/레시피도 DB 영속화 |
| H2 | `law_client.py:294` `get_relevant_articles` | LAW_API(law.go.kr)가 **호출 서버 IP/도메인 등록**을 요구 → 현재 “사용자 정보 검증 실패”. (크래시는 없음: 키 없거나 실패 시 `[]` 반환 후 RAG fallback) | EC2 고정 IP/도메인을 law.go.kr OPEN API에 등록 (외부 작업·결정 필요, `results_law.md` 참고) |

## [중] 안정성 흠

| # | 위치 | 왜 문제 | 수정안(제안) |
|---|------|---------|-------------|
| M1 | `main.py` `funding_register`(~1098) · `approve_drink_request`(~1012) | Gemini `auto_pipeline.create_taste_vector(use_gemini=True)` 가 try 안에 있어 **Gemini 실패 시 500**. approve는 all-zero 시 기본벡터 fallback 있으나 예외 자체는 미처리 | pipeline 호출을 try/except로 감싸고 실패 시 `_create_basic_vector` fallback. (`image/generate`는 이미 prompt_only fallback 보유 — 양호) |
| M2 | `ocr.py` `extract_brewery_info`(15) · `image_generator._decode_base64`(72) | **base64 입력 크기·형식 검증 없음.** 초대형/깨진 base64 → 메모리 급증·Gemini 오류. FastAPI 기본 body 제한 외 가드 없음 | 디코드 전 길이 상한(예: ~10MB) + `try except` 디코드 가드 + mime 화이트리스트 |
| M3 | `main.py` `bti_feedback`(~582) | 핸들러에 **외부 try/except 없음.** DB 실패 후 JSON 파일쓰기 실패 시 미처리 500 (db 메서드 내부 처리에 의존) | 핸들러 전체 try/except + 실패 시 graceful 에러 응답 |
| M4 | HTTPException 삼킴 패턴(공통) | `except Exception as e: 500` 앞에 `except HTTPException: raise` 가 없으면 의도한 4xx가 500이 됨. recommend는 수정함. 점검 결과 다른 핸들러는 대부분 검증 가드를 try **밖**에 둬 안전 | 핸들러 작성 규약화: 항상 `except HTTPException: raise` 선행 |

## [하] 경미 / 데모엔 무해

| # | 위치 | 메모 |
|---|------|------|
| L1 | `main.py:363` `/health` | bti_feedback.json 인라인 로드·파싱. 실패 시 health가 `{status:error}` (전체 try/except로 크래시는 아님) |
| L2 | `main.py` `_drink_request_id_counter` | 비원자적 증가 — 다중 워커/동시요청 시 ID 충돌 가능. 단일 워커면 무해 |
| L3 | `law_rag.py:20` ChromaDB `EphemeralClient` | 재시작마다 재적재(startup). 적재/검색 실패 시 `[]` 반환(안전). 영속성 없음 → `results_law.md` D에서 다룸 |
| L4 | `survey_converter.py:190` `determine_bti_code_hybrid` | KNN 모델 없으면 rule 반환, 로드 실패도 try/except — **fallback 안전** (확인됨) |
| L5 | `recommend`/`recipe` 외부호출 | DB 미연결 시 `db_connected` 체크 후 메모리 fallback 일관 적용 — 양호 |

---

## 외부 의존성별 안전망 요약
| 의존성 | 실패 시 | 안전망 |
|--------|---------|--------|
| Gemini | 503 또는 `disabled`/`prompt_only` | chat/law/insight/image 대부분 graceful, **funding/approve는 500(M1)** |
| DB(Postgres) | `db_connected=False` | 메모리+JSON fallback 일관 적용(양호). 단 메모리는 재시작 소실(H1) |
| 농사로 API | 수집 스크립트 단계 | `ingredient-region`은 수집 json 없으면 하드코딩 fallback(양호) |
| LAW API | 인증/IP 실패 | `[]` 반환 → 내장 9법령 RAG fallback(양호, 단 실시간 조문 비활성 H2) |
| ChromaDB | 초기화/검색 실패 | `[]` 반환(안전) |
| S3 | — | AI 서버는 S3 미사용. 이미지 base64 반환만, 저장은 백엔드 몫(설계상 정상) |

## 결론
- **크래시 수준 버그는 적음** — 대부분 try/except·fallback 보유. recommend 1건만 코드 수정.
- 발표 전 **반드시 확인**: H1(재시작 데이터 소실 → 단일 인스턴스 유지), H2(LAW IP 등록).
- 권장 후속(제안): M1(펀딩/승인 Gemini fallback), M2(base64 크기 가드).
