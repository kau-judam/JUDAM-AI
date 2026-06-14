# 주담 AI 서버 팀 업데이트

## A. 이번 변경 사항

- **OCR (`POST /api/brewery/verify-ocr`)**: JSON/base64 요청에서 `multipart/form-data` 파일 업로드로 전환했습니다. `python-multipart` 의존성이 추가되었습니다.
- **서브재료 (`POST /api/recipe/suggest-sub-ingredients`)**: 실제 지역 후보 안에서 Gemini가 궁합을 보조 선별하며, 실패하면 기존 후보 목록으로 폴백합니다. 응답 모델은 변경되지 않았습니다.
- **챗봇 (`POST /api/chat`)**: 실제 카탈로그 제품만 선택한 뒤 Gemini가 큐레이션 답변을 생성합니다. 목록 밖 제품은 차단하고 Gemini 실패 시 카탈로그 기반 템플릿으로 폴백합니다. 멀티턴은 서버 무상태이며 클라이언트가 매 요청에 `history`를 전달해야 합니다. 응답 모델은 변경되지 않았습니다.
- **서브재료 2단계 흐름**: `GET /api/recipe/ingredient-region`으로 재료의 생산 지역 목록을 조회한 뒤, 사용자가 고른 지역과 재료를 `POST /api/recipe/suggest-sub-ingredients`에 전달합니다.
- **BTI 피드백 (`POST /api/bti/feedback`)**: `wrong_axes`와 `feedback_reason` Optional 필드를 추가했습니다. 두 필드는 요청 오류 없이 수집하지만 현재 DB 컬럼과 KNN 학습에는 반영되지 않습니다.

## B. 배포 담당 승빈 확인사항

- `main` 최신 커밋을 pull합니다. 기능·가이드·팀 문서를 포함한 배포 기준 커밋은 `659a37b`입니다.
- `python-multipart`가 추가되었으므로 반드시 `pip install -r requirements.txt`를 실행합니다. 재설치하지 않으면 OCR multipart 요청 처리가 실패합니다.
- PM2의 `judam-ai-server`, `judam-ai-sqs-worker`를 모두 재시작합니다.
- `GEMINI_API_KEY` 존재 여부를 확인합니다. 챗봇 큐레이션, 서브재료 선별, 후속 질문 생성에 사용하며 미설정·호출 실패 시 폴백되지만 품질이 낮아집니다.

## C. 프론트 강민재·권아영 확인사항

- 챗봇 화면에서 "특정 브랜드 술 추천"이 거절되지 않고 실제 제품명으로 답하는지 확인합니다. 일반 추천에도 실제 제품명이 포함되어 배포 전 구버전 증상이 사라졌는지 확인합니다.
- 서브재료는 `재료 입력 → ingredient-region 호출 → 지역 선택 → suggest-sub-ingredients 호출` 순서로 연동합니다. `region`은 사용자가 임의 입력하는 값이 아니라 지역 조회 응답의 `regions` 중 선택한 값을 전달합니다.
- BTI 피드백은 `wrong_axes`에 틀린 축 배열, `feedback_reason`에 이유를 전달할 수 있습니다. 둘 다 선택 필드입니다.
- **확인 필요, 미해결**: BTI 피드백 제출 시 `user_id`를 항상 보내는지 확인해야 합니다. 비로그인 게스트도 피드백할 수 있다면 현재 `user_id` 필수 계약 때문에 HTTP 422가 발생합니다. 게스트 피드백이 필요하면 AI 서버의 `user_id` Optional 처리가 별도 필요합니다.

## D. 배포 후 검증 체크리스트

- [ ] PNG 한 장을 multipart로 `/api/brewery/verify-ocr`에 호출해 HTTP 200이며 `body.status`가 `FAILED`가 아닌지 확인
- [ ] `/api/chat`에 `"소고기랑 먹기 좋은 술 추천"`을 보내 실제 제품명이 포함된 큐레이션 답변인지 확인
- [ ] `/api/chat`에 `"특정 브랜드 술 추천"`을 보내 거절하지 않는지 확인
- [ ] `/api/recipe/ingredient-region?ingredient=사과`가 지역 목록을 반환하는지 확인
- [ ] 선택 지역으로 `{"main_ingredient":"사과","region":"청주시"}`를 `/api/recipe/suggest-sub-ingredients`에 보내 서브재료를 반환하는지 확인
- [ ] `/api/bti/feedback`에 `wrong_axes`와 `feedback_reason`을 포함해 호출했을 때 HTTP 200인지 확인

## E. 알려진 사항

- `google.generativeai` 구 SDK의 FutureWarning이 출력될 수 있지만 현재 동작에는 영향이 없습니다. 신 SDK 통일은 추후 별도 작업입니다.
- `/api/chat/stream`은 이번 큐레이션 통합 대상이 아니며 별도의 구버전 Gemini 본문을 사용합니다. 프론트가 `/api/chat`과 `/api/chat/stream` 중 어느 경로를 사용하는지 확인해야 합니다.
- BTI 피드백의 `wrong_axes`와 `feedback_reason`은 현재 수집 전용이며 DB와 KNN 학습에는 반영되지 않습니다.

## 관련 커밋

- BTI 피드백 Optional 필드: `e976829` (`feat: BTI 피드백 상세 사유를 선택 수집`)
- API 가이드 보강: `ac71366` (`docs: BTI 피드백과 서브재료 연동 계약 보강`)
- 기존 OCR multipart·관리자 검토 정책: `510c1ef`
- 기존 챗봇·서브재료 Gemini 큐레이션: `f21839d`
- 기존 AI API 가이드·인수인계 동기화: `1f761e8`
- 기능·가이드·팀 문서 배포 기준 main: `659a37b`
