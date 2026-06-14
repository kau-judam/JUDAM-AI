# 주담 AI 서버 팀 인수인계 메모

## 배포 필수사항

- `requirements.txt`에 `python-multipart`가 추가되었습니다. OCR multipart 요청을 받으려면 배포 환경에서 `pip install -r requirements.txt`를 다시 실행해야 합니다.
- 의존성 설치 후 PM2의 `judam-ai-server`, `judam-ai-sqs-worker`를 재시작합니다.
- 재시작 전후 `GET /health`를 호출해 서버 상태와 `gemini_key_loaded`, `gemini_available`, `db_connected`를 비교합니다.
- 현재 로컬 Windows 작업 환경에서는 PM2와 Python 실행 환경을 확인할 수 없었습니다. 실제 서버에서 위 절차를 수행해야 합니다.

## 환경변수와 모델

- `GEMINI_API_KEY`는 챗봇 본문 큐레이션, 챗봇 후속 질문, 서브재료 후보 선별에 사용됩니다.
- 키가 없거나 Gemini 호출이 실패하면 챗봇은 실제 카탈로그 기반 템플릿, 서브재료는 기존 지역 후보 목록으로 안전하게 폴백합니다. 기능은 유지되지만 큐레이션 품질은 낮아집니다.
- 챗봇 본문·후속 질문·서브재료 선별은 `gemini-2.5-flash-lite`를 사용합니다.
- `google.generativeai` 구 SDK는 실행 시 FutureWarning을 출력할 수 있으나 현재 동작에는 영향이 없습니다. 신 SDK 통일은 별도 작업입니다.

## 백엔드 전달사항

- `POST /api/brewery/verify-ocr`는 반드시 `multipart/form-data`로 호출합니다. JSON/base64 요청은 현재 엔드포인트 계약이 아니며 과거 파일 bytes를 JSON/UTF-8로 처리하면서 발생한 `UnicodeDecodeError`의 원인이었습니다.
- OCR 파일 필드는 실제 백엔드 공식 필드를 확인하지 못해 현재 `file`과 `businessLicense`를 임시 호환합니다.
- OCR 업무 실패도 HTTP 200이며 `body.status="FAILED"`와 `summary.reason`을 확인해야 합니다. OCR 결과는 관리자 검토 자료일 뿐 자동 승인·반려에 사용하지 않습니다.
- `documentUrl`, `documentKey`, `originalName`과 snake_case alias는 현재 AI 서버 OCR 처리나 DB 저장에 사용하지 않습니다. `mimeType`/`mime_type`은 업로드 content type이 없을 때만 보조 검증에 사용합니다.
- AI 서버 저장소에는 인증 신청 저장 흐름과 `brewery_auth.ocr_status` 저장 코드가 없어 해당 통합은 미검증입니다.

## 프론트 전달사항

- 서브재료 UI는 `GET /api/recipe/ingredient-region?ingredient=사과`로 지역 목록을 받은 뒤 사용자가 지역을 선택하고, `POST /api/recipe/suggest-sub-ingredients`에 `{"main_ingredient":"사과","region":"청주시"}`를 전달합니다.
- `/api/chat`은 서버 무상태입니다. 멀티턴 맥락을 유지하려면 매 요청에 이전 메시지와 assistant 응답의 `referenced_drinks`를 `history` 배열로 다시 전달합니다.
- `next_actions`와 기존 호환 필드 `suggested_questions`는 같은 후속 질문 목록입니다.
- `/api/chat/stream`은 이번 카탈로그 제한·개인화 큐레이션 통합 대상이 아닙니다. `session_id`도 현재 저장 또는 멀티턴 유지에 사용되지 않으므로 프론트가 어느 챗봇 엔드포인트를 사용하는지 확인해야 합니다.

## 배포 전후 검증 체크리스트

- [ ] 배포 환경에서 `python -m pytest tests/ -q`
- [ ] `python -m py_compile`로 변경 Python 파일 문법 확인
- [ ] FastAPI `app.main:app` import 확인
- [ ] 배포 전 `GET /health` 응답 기록
- [ ] 의존성 재설치 후 `judam-ai-server`, `judam-ai-sqs-worker` 재시작
- [ ] 배포 후 `GET /health` 확인
- [ ] PNG 한 장을 multipart `file` 또는 실제 백엔드 필드로 `/api/brewery/verify-ocr`에 전송
- [ ] OCR 응답이 HTTP 200이며 `verified=false`, `manualReviewOnly=true`인지 확인
- [ ] `/api/chat`에 `{"message":"소고기에 어울리는 전통주 추천해줘"}` 호출 후 `referenced_drinks` 제품명만 본문에 등장하는지 확인
- [ ] 직전 chat 응답을 `history`에 넣고 `"그중 낮은 도수는?"` 호출
- [ ] `ingredient-region?ingredient=사과` 지역 선택 후 `suggest-sub-ingredients` 호출
- [ ] Gemini 실패 상황에서 챗봇 템플릿과 서브재료 기존 후보 폴백 확인

## 현재 검증 한계

- 이 문서 작성 환경에는 실행 가능한 Python, pytest, PM2가 없어 테스트와 서버 재시작을 수행하지 못했습니다.
- Public/Private Base URL은 현재 작업 환경에서 연결되지 않아 배포 서버의 실제 HTTP 응답은 확인하지 못했습니다.
- PDF OCR은 코드 경로와 mock 테스트만 존재하며 실제 Gemini PDF 호출은 라이브 미검증입니다.
