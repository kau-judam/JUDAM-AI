# 주담 AI 서버 — 백엔드 연동 가이드

## AI 서버 정보
- EC2 내부 주소: http://10.0.11.241:8000
- 헬스체크: GET /health

## 1. 회원가입/설문 완료 후 플로우
프론트에서 설문 완료 → 백엔드로 전송 → 백엔드가 AI 서버 호출

백엔드 → AI 서버:
```
POST http://10.0.11.241:8000/api/survey/convert?user_id={user_id}
Body: { q1~q25 설문 응답값 }
```

AI 서버 응답에서 백엔드 DB 저장 항목:
- `taste_vector` (JSON): 8축 맛벡터 → users 테이블
- `bti_code` (string): 5글자 BTI 코드 → users 테이블
- `character_name` (string): BTI 캐릭터명 → users 테이블
- `experience_level` (string): 경험 수준 → users 테이블
- `preferred_abv` (string): 선호 도수 → users 테이블
- `preferred_body` (string): 선호 바디감 → users 테이블
- `preferred_fruit` (string): 선호 과일 → users 테이블
- `preferred_food_pairing` (array): 선호 안주 → users 테이블
- `preferred_aroma` (array): 선호 향기 → users 테이블
- `taste_profile_summary` (string): 취향 요약 → users 테이블
- `alcohol_label` (string): 고도수/저도수 → users 테이블

## 2. 전통주 추천 플로우
```
POST http://10.0.11.241:8000/api/recommend
```
Body:
```json
{
  "user_vector": {
    "sweetness": 8.14,
    "body": 2.64,
    "carbonation": 8.29,
    "flavor": 7.84,
    "alcohol": 3.6,
    "acidity": 7.71,
    "aroma_intensity": 7.21,
    "finish": 4.43
  },
  "top_k": 10
}
```

AI 서버 응답:
```json
[
  {
    "id": "makgeolli_001",
    "name": "복순도가 손막걸리",
    "similarity": 0.94,
    "similarity_percent": 94.0,
    "match_reason": ["단맛이 잘 맞아요", "탄산감이 잘 맞아요"],
    "is_funding": false,
    "status": "available",
    "abv": 6.5,
    "brewery": "복순도가",
    "region": "경북 울진",
    "taste_vector": { "..." : "..." }
  }
]
```

## 3. 챗봇 플로우
```
POST http://10.0.11.241:8000/api/chat
```
Body:
```json
{
  "message": "사용자 질문",
  "user_id": "user_001",
  "history": [
    {"role": "user", "content": "이전 질문"},
    {"role": "assistant", "content": "이전 답변"}
  ]
}
```
`history` 최대 10개 권장, `user_id` 있으면 개인화 답변

응답:
```json
{
  "response": "답변 텍스트",
  "context": "traditional_korean_alcohol",
  "suggested_questions": ["후속 질문1", "후속 질문2"]
}
```
`context`가 `out_of_scope`면 전통주 비관련 질문

## 4. 레시피/펀딩 법률 검토 플로우
콘텐츠 등록 전 반드시 호출:
```
POST http://10.0.11.241:8000/api/law/filter
```
Body:
```json
{
  "content_type": "recipe",
  "title": "레시피/펀딩 제목",
  "description": "설명 텍스트",
  "ingredient_names": ["재료1", "재료2"]
}
```
`content_type`: `"recipe"` 또는 `"product_description"`

응답:
```json
{
  "violation": true,
  "details": ["위반 내용"],
  "recommendation": "수정 권고사항"
}
```
`violation: true` → 프론트에 경고 표시, 등록 불가 처리

## 5. 펀딩 등록 플로우
```
POST http://10.0.11.241:8000/api/funding/register
```
Body:
```json
{
  "funding_id": "funding_001",
  "name": "막걸리 이름",
  "brewery": "양조장명",
  "brewery_user_id": "user_id",
  "region": "지역",
  "abv": 6.0,
  "main_ingredient": "메인 재료",
  "description": "설명",
  "taste_input": {
    "sweetness": 7, "body": 4, "carbonation": 6,
    "flavor": 7, "alcohol": 4, "acidity": 5,
    "aroma_intensity": 6, "finish": 5
  }
}
```
`taste_input` 없으면 Gemini 자동 생성 (품질 낮음, 권장하지 않음)

응답:
```json
{
  "status": "success",
  "funding_id": "funding_001",
  "taste_vector": { "..." : "..." },
  "source": "direct_input",
  "message": "펀딩 전통주가 추천 풀에 편입되었습니다."
}
```

## 6. 사용자 시음 평가 → 취향 업데이트
```
POST http://10.0.11.241:8000/api/taste/update
```
Body:
```json
{
  "user_id": "user_001",
  "drink_id": "makgeolli_001",
  "rating": 4,
  "ratings": {
    "sweetness": 7, "body": 4, "carbonation": 6,
    "flavor": 7, "alcohol": 4, "acidity": 5,
    "aroma_intensity": 6, "finish": 5
  },
  "tags": ["달콤한", "청량한"]
}
```
`rating`(별점 1~5) 또는 `ratings`(축별 0~10) 중 하나 필수

## 7. 신규 전통주 등록 요청 (크라우드소싱)
```
POST http://10.0.11.241:8000/api/drinks/request
```
Body:
```json
{
  "user_id": "user_001",
  "name": "전통주 이름",
  "brewery": "양조장명",
  "region": "지역",
  "description": "설명"
}
```

관리자 승인:
```
POST http://10.0.11.241:8000/api/drinks/requests/{request_id}/approve
```

## 8. 에러 처리

| HTTP 코드 | 의미 | 처리 방법 |
|-----------|------|-----------|
| 400 | 잘못된 입력값 | `message` 필드 확인 후 프론트 안내 |
| 404 | 리소스 없음 | 해당 ID 존재 여부 확인 |
| 503 | Gemini 서비스 점검 중 | 잠시 후 재시도 안내 |
| 500 | 서버 오류 | 관리자 알림 |

## 9. 주의사항
- `user_profiles`는 인메모리 + DB 이중 저장. 서버 재시작 시 인메모리 초기화되지만 DB에서 자동 복구
- Gemini API 한도 초과 시 503 반환. `gemini_available: false`면 레시피/법률/챗봇 API 제한됨
- 추천 결과 `is_funding: true`인 항목은 펀딩 중인 전통주. 프론트에서 펀딩 배지 표시 권장
