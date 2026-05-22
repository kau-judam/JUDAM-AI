# 백엔드 연동 가이드

주담 AI 서버(`juddam-ai`)와 백엔드 서버 간 연동 흐름을 정리한 문서입니다.

---

## 공통 주의사항

- **Base URL (EC2)**: `http://43.202.24.223:8000`
- **Content-Type**: `application/json`
- **에러 형식**: `{ "status": "error", "message": "한국어 메시지" }`
- **GEMINI_AVAILABLE: false 시**: HTTP 503 반환 → 백엔드에서 재시도 처리 또는 사용자에게 안내
- **user_profiles**: 현재 인메모리 → 서버 재시작 시 초기화. 재시작 후 필요 시 survey/convert 재호출 또는 recommend에 user_vector 직접 전달

---

## 1. 설문 완료 후 추천 플로우

```
[프론트] 술BTI 설문 완료
    ↓
[백엔드] POST /api/survey/convert?user_id={user_id}
    ↓
[AI 서버] taste_vector, bti_code, character_name 등 반환
    ↓
[백엔드] 응답 전체를 백엔드 DB(users 테이블)에 저장
    ↓
[프론트] 추천 요청
    ↓
[백엔드] POST /api/recommend  ← user_vector 직접 전달 (DB에서 꺼내서)
```

### 설문 변환 호출

```http
POST /api/survey/convert?user_id=user123
Content-Type: application/json

{ "q1": 2, "q2": 2, ..., "q24": [1, 4], "q25": [1, 2] }
```

### 추천 호출 (user_vector 직접 전달 권장)

```http
POST /api/recommend
Content-Type: application/json

{
  "user_vector": {
    "sweetness": 8.14, "body": 2.64, "carbonation": 8.29,
    "flavor": 7.84, "alcohol": 3.6, "acidity": 7.71,
    "aroma_intensity": 7.21, "finish": 4.43
  },
  "top_k": 10
}
```

### 추천 응답에서 확인할 필드

| 필드 | 설명 |
|------|------|
| `similarity_percent` | 유사도 퍼센트 (예: 97.8) — UI 표시용 |
| `is_funding` | 펀딩 중인 전통주 여부 (true/false) |
| `status` | `"available"` 또는 `"funding"` |
| `match_reason` | 추천 이유 한국어 2개 — UI 표시용 |

---

## 2. 펀딩 등록 플로우

```
[양조장] 펀딩 등록 페이지에서 레시피 작성
    ↓
[백엔드] POST /api/funding/register  (taste_input 포함 권장)
    ↓
[AI 서버] 추천 풀 즉시 편입 + funding_id 저장
    ↓
[양조장] 샘플 시음 후 수치 보정
    ↓
[백엔드] POST /api/funding/{funding_id}/taste-update
    ↓
[AI 서버] 추천 풀 실시간 반영
```

### 펀딩 등록 호출

```http
POST /api/funding/register
Content-Type: application/json

{
  "funding_id": "funding_001",
  "name": "경기도 이천 쌀 막걸리",
  "brewery": "이천 양조장",
  "region": "경기도 이천",
  "abv": 6.0,
  "main_ingredient": "이천 쌀",
  "taste_input": {
    "sweetness": 8, "body": 4, "carbonation": 7, "flavor": 6,
    "alcohol": 4, "acidity": 5, "aroma_intensity": 6, "finish": 5
  },
  "brewery_user_id": "brewery_001"
}
```

> `taste_input` 없이 호출하면 Gemini가 자동 생성 (`GEMINI_AVAILABLE=true`일 때만).

---

## 3. 레시피 등록 플로우

```
[사용자] 레시피 작성 완료
    ↓
[백엔드] POST /api/recipe/validate  ← 제작 가능성 검토 (선택)
    ↓
[AI 서버] feasibility / score / issues / suggestions 반환
    ↓
[백엔드] score가 충분하면 등록 허용
    ↓
[백엔드] POST /api/recipe/register
    ↓
[AI 서버] 추천 풀 편입
```

### 레시피 검토 호출

```http
POST /api/recipe/validate
Content-Type: application/json

{
  "title": "이천 쌀 막걸리",
  "main_ingredient": "이천 쌀",
  "sub_ingredients": ["가평 잣", "여주 고구마"],
  "abv_range": "6~8도",
  "flavor_tags": ["달콤한", "고소한"],
  "description": "구수하고 달콤한 막걸리"
}
```

응답의 `feasibility`가 `"low"`이면 등록 차단 또는 개선 안내를 권장합니다.

---

## 4. 법률 필터링 플로우

```
[사용자/양조장] 레시피 또는 펀딩 콘텐츠 등록
    ↓
[백엔드] POST /api/law/filter  ← 콘텐츠 등록 전 반드시 호출
    ↓
[AI 서버] violation: true/false 반환
    ↓
[백엔드] violation: true이면 등록 차단 + details/recommendation 사용자에게 표시
```

```http
POST /api/law/filter
Content-Type: application/json

{
  "content_type": "recipe",
  "title": "콘텐츠 제목",
  "description": "콘텐츠 설명",
  "ingredients": ["쌀", "누룩", "물"]
}
```

---

## 5. 챗봇 플로우

```
[사용자] 채팅 메시지 입력
    ↓
[백엔드] POST /api/chat  (history 포함 전달)
    ↓
[AI 서버] response + suggested_questions 반환
    ↓
[프론트] 응답 표시 + 후속 질문 버튼 표시
```

```http
POST /api/chat
Content-Type: application/json

{
  "message": "막걸리 추천해줘",
  "user_id": "user123",
  "history": [
    { "role": "user", "content": "이전 질문" },
    { "role": "assistant", "content": "이전 답변" }
  ]
}
```

- `user_id`로 survey/convert 프로필이 있으면 BTI 기반 개인화 답변 제공
- `history`는 최근 대화 5~10턴 권장

---

## 6. 에러 처리 가이드

| HTTP 코드 | 상황 | 백엔드 처리 |
|-----------|------|------------|
| 400 | 입력값 오류 | `message` 필드를 프론트에 그대로 표시 |
| 404 | 리소스 없음 | 등록 유도 또는 재시도 안내 |
| 503 | Gemini 점검/한도 | "AI 서비스 점검 중" 안내 + 잠시 후 재시도 |
| 500 | 서버 내부 오류 | 로그 기록 + "잠시 후 다시 시도" 안내 |

---

## 7. 서버 상태 모니터링

배포 후 주기적으로 `/health`를 호출해 상태를 확인합니다.

```http
GET /health
```

- `gemini_available: false` → Gemini 관련 기능 비활성 상태
- `db_connected: false` → DB 연결 실패, 인메모리로만 동작 (재시작 시 데이터 유실 주의)
- `uptime_seconds` → 서버 재시작 여부 확인용
