# 주담 AI 서버 API 가이드

## 서버 정보

| 환경 | URL |
|------|-----|
| 로컬 개발 | http://localhost:8000 |
| EC2 프록시 | http://43.202.24.223:3000/api/ai |
| Swagger UI | http://localhost:8000/docs (로컬만) |

## 공통 응답 형식

성공 시 HTTP 200, 에러 시 HTTP 4xx/5xx 반환

```json
{
  "detail": "에러 메시지"
}
```

---

## 1. GET /health

헬스체크 엔드포인트. 서버 상태 확인용.

### Request
없음

### Response

```json
{
  "status": "ok",
  "data_count": 207,
  "user_count": 0,
  "gemini_key_loaded": true,
  "db_connected": true
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| status | string | 서버 상태 ("ok" 또는 "error") |
| data_count | number | 로드된 전통주 데이터 수 |
| user_count | number | 사용자 수 |
| gemini_key_loaded | boolean | Gemini API 키 로드 여부 |
| db_connected | boolean | PostgreSQL 연결 여부 |

### curl 예시

```bash
curl http://localhost:8000/health
```

### 에러 케이스
- 서버가 실행 중이 아닌 경우: 연결 거부

---

## 2. POST /api/recommend

맛 벡터 기반 전통주 추천. 코사인 유사도로 가장 유사한 전통주를 추천합니다.

### Request Body

```json
{
  "user_vector": {
    "sweetness": 7.5,
    "body": 5.0,
    "carbonation": 3.0,
    "flavor": 6.5,
    "alcohol": 4.0,
    "acidity": 5.0,
    "aroma_intensity": 5.0,
    "finish": 5.0
  },
  "top_k": 10,
  "exclude_ids": []
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| user_vector | object | O | 사용자 맛 벡터 (0~10) |
| user_vector.sweetness | number | O | 단맛 (0~10) |
| user_vector.body | number | O | 바디감 (0~10) |
| user_vector.carbonation | number | O | 탄산 (0~10) |
| user_vector.flavor | number | O | 풍미 (0~10) |
| user_vector.alcohol | number | O | 도수 (0~10) |
| user_vector.acidity | number | O | 산미 (0~10) |
| user_vector.aroma_intensity | number | O | 향기 강도 (0~10) |
| user_vector.finish | number | O | 여운 (0~10) |
| top_k | number | X | 추천할 상위 k개 (기본값: 10) |
| exclude_ids | array | X | 제외할 ID 리스트 |

### Response

```json
[
  {
    "id": "makgeolli_0",
    "name": "이동 생 쌀 막걸리",
    "similarity": 0.95,
    "abv": 6.0,
    "brewery": "이동양조",
    "region": "경기도",
    "features": "맑고 깨끗한 맛",
    "taste_vector": {
      "sweetness": 7.0,
      "body": 5.0,
      "carbonation": 3.0,
      "flavor": 6.0,
      "alcohol": 4.0,
      "acidity": 5.0,
      "aroma_intensity": 5.0,
      "finish": 5.0
    }
  }
]
```

| 필드 | 타입 | 설명 |
|------|------|------|
| id | string | 전통주 ID |
| name | string | 전통주 이름 |
| similarity | number | 유사도 (0~1) |
| abv | number | 알콜 도수 (%) |
| brewery | string | 양조장 |
| region | string | 지역 |
| features | string | 특징 |
| taste_vector | object | 맛 벡터 |

### curl 예시

```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_vector": {
      "sweetness": 7.5,
      "body": 5.0,
      "carbonation": 3.0,
      "flavor": 6.5,
      "alcohol": 4.0,
      "acidity": 5.0,
      "aroma_intensity": 5.0,
      "finish": 5.0
    },
    "top_k": 5
  }'
```

### 에러 케이스
- 500: 데이터 로드 실패

---

## 3. POST /api/survey/convert

술BTI 설문 응답 → 맛 벡터 변환. 25문항 설문 결과를 8축 맛 벡터로 변환합니다.

### Request Body

```json
{
  "q1": 3,
  "q2": 3,
  "q3": 3,
  "q4": 5,
  "q5": 4,
  "q6": 4,
  "q7": 5,
  "q8": 4,
  "q9": 4,
  "q10": 4,
  "q11": 4,
  "q12": 4,
  "q13": 4,
  "q14": 3,
  "q15": 4,
  "q16": 4,
  "q17": 3,
  "q18": 5,
  "q19": 4,
  "q20": 3,
  "q21": 3,
  "q22": 4,
  "q23": 1,
  "q24": [1, 2, 3],
  "q25": [1, 2]
}
```

| 필드 | 타입 | 범위 | 설명 |
|------|------|------|------|
| q1~q3 | number | 1~5 | 서열척도 (전통주 경험, 선호 도수, 선호 바디감) |
| q4~q22 | number | 1~7 | 등간척도 Likert (맛/향/바디감 선호도) |
| q23 | number | 1~5 | 선호 과일 (명목척도) |
| q24 | array | - | 음식 페어링 선호 (복수선택) |
| q25 | array | - | 관심 향 (복수선택) |

### Response

```json
{
  "status": "success",
  "taste_vector": {
    "sweetness": 5.5,
    "body": 5.0,
    "carbonation": 4.5,
    "flavor": 5.5,
    "alcohol": 5.0,
    "acidity": 5.0,
    "aroma_intensity": 5.0,
    "finish": 5.0
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| status | string | 변환 상태 ("success") |
| taste_vector | object | 변환된 맛 벡터 |

### curl 예시

```bash
curl -X POST http://localhost:8000/api/survey/convert \
  -H "Content-Type: application/json" \
  -d '{
    "q1": 3,
    "q2": 3,
    "q3": 3,
    "q4": 5,
    "q5": 4,
    "q6": 4,
    "q7": 5,
    "q8": 4,
    "q9": 4,
    "q10": 4,
    "q11": 4,
    "q12": 4,
    "q13": 4,
    "q14": 3,
    "q15": 4,
    "q16": 4,
    "q17": 3,
    "q18": 5,
    "q19": 4,
    "q20": 3,
    "q21": 3,
    "q22": 4,
    "q23": 1,
    "q24": [1, 2, 3],
    "q25": [1, 2]
  }'
```

### 에러 케이스
- 422: 유효하지 않은 설문 응답
- 500: 변환 실패

---

## 4. POST /api/survey/bti-type

맛 벡터 → 술BTI 유형 코드 + 캐릭터 반환. 16가지 술BTI 유형 중 하나를 판정합니다.

### 판단 로직

| 코드 | 1글자 | 2글자 | 3글자 | 4글자 |
|------|-------|-------|-------|-------|
| 조건 | sweetness | body | carbonation | flavor |
| S/H | >= 5 → S | >= 5 → H | >= 5 → F | >= 5 → U |
| D/L | < 5 → D | < 5 → L | < 5 → M | < 5 → C |

### 16가지 술BTI 유형

| 코드 | 캐릭터명 | 추천 전통주 |
|------|----------|------------|
| SHFC | 꿀단지에 빠진 인절미 | 꿀 막걸리, 밤 막걸리, 탄산 생막걸리 |
| SHFU | 탄산 톡톡 딸기 요거트 | 딸기 탄산막걸리, 복숭아 생막걸리, 유자 탁주 |
| SHMC | 쫀득쫀득 꿀 찹쌀떡 | 찹쌀탁주, 원주 막걸리, 고구마 막걸리 |
| SHMU | 포근포근 꽃복숭아 | 망고 막걸리, 블루베리 탁주, 샤인머스캣 막걸리 |
| SLFC | 청량함 가득 사과 푸딩 | 저도수 생막걸리, 쌀 막걸리, 캔 막걸리 |
| SLFU | 팝핑 과일 에이드 | 자몽 막걸리, 레몬 탁주, 오미자 탄산막걸리 |
| SLMC | 햇살 머금은 식혜 | 맑은 탁주, 단술, 저도수 쌀막걸리 |
| SLMU | 산들바람 머금은 화전 | 꽃잎 막걸리, 허브 탁주, 사과 막걸리 |
| DHFC | 바삭하게 터지는 현미 누룽지 | 고도수 생막걸리, 드라이한 탁주, 호밀 막걸리 |
| DHFU | 반전매력 고추냉이 | 오미자 탄산막걸리, 생강 탁주, 쑥 막걸리 |
| DHMC | 묵묵한 바위 속 숭늉 | 무감미료 탁주, 고도수 원주, 옥수수 막걸리 |
| DHMU | 안개 낀 숲속의 황금사과 | 산미 특화 막걸리, 약재 향 탁주, 드라이 과일막걸리 |
| DLFC | 청량한 대나무 숲의 차 | 가벼운 드라이 막걸리, 탄산 약주, 쌀 생막걸리 |
| DLFU | 차가운 도시의 샹그리아 | 드라이 유자막걸리, 진저 탁주, 탄산 베리막걸리 |
| DLMC | 대숲에 앉은 맑은 백설기 | 정통 드라이 탁주, 맑은 막걸리, 가벼운 누룩주 |
| DLMU | 빗소리 들리는 다실의 꽃차 | 산미 있는 가벼운 탁주, 허브 드라이막걸리, 차 콜라보 막걸리 |

### Request Body

```json
{
  "sweetness": 8.0,
  "body": 7.0,
  "carbonation": 3.0,
  "flavor": 4.0
}
```

| 필드 | 타입 | 범위 | 설명 |
|------|------|------|------|
| sweetness | number | 0~10 | 단맛 |
| body | number | 0~10 | 바디감 |
| carbonation | number | 0~10 | 탄산 |
| flavor | number | 0~10 | 풍미 |

### Response

```json
{
  "code": "SHMC",
  "character_name": "쫀득쫀득 꿀 찹쌀떡",
  "tags": ["#부드러운단맛", "#화사한과일향"],
  "recommended_drinks": ["찹쌀탁주", "원주 막걸리", "고구마 막걸리"]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| code | string | 4글자 술BTI 코드 |
| character_name | string | 캐릭터명 |
| tags | array | 태그 리스트 |
| recommended_drinks | array | 추천 전통주 리스트 |

### curl 예시

```bash
curl -X POST http://localhost:8000/api/survey/bti-type \
  -H "Content-Type: application/json" \
  -d '{
    "sweetness": 8.0,
    "body": 7.0,
    "carbonation": 3.0,
    "flavor": 4.0
  }'
```

### 에러 케이스
- 422: 유효하지 않은 맛 벡터 값
- 500: 판정 실패

---

## 5. POST /api/recipe/suggest-sub-ingredients

메인재료 입력 시 지역 특산물 기반 서브재료 추천. Gemini API를 활용합니다.

### Request Body

```json
{
  "main_ingredient": "경기도 쌀",
  "region": "경기도"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| main_ingredient | string | O | 메인 재료 |
| region | string | O | 지역 |

### Response

```json
{
  "sub_ingredients": ["누룩", "물", "유자", "생강", "꿀"]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| sub_ingredients | array | 서브재료 리스트 (최대 5개) |

### curl 예시

```bash
curl -X POST http://localhost:8000/api/recipe/suggest-sub-ingredients \
  -H "Content-Type: application/json" \
  -d '{
    "main_ingredient": "경기도 쌀",
    "region": "경기도"
  }'
```

### 에러 케이스
- 500: GEMINI_API_KEY가 설정되지 않은 경우 빈 배열 반환
- 500: Gemini API 호출 실패

---

## 6. POST /api/recipe/suggest-flavor-tags

레시피 정보 기반 맛 태그 자동 생성. Gemini API를 활용합니다.

### Request Body

```json
{
  "title": "경기도 쌀 막걸리",
  "main_ingredient": "경기도 쌀",
  "sub_ingredients": ["누룩", "물"],
  "abv_range": "5~7도"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| title | string | O | 제목 |
| main_ingredient | string | O | 메인 재료 |
| sub_ingredients | array | X | 서브 재료 |
| abv_range | string | O | 도수 범위 |

### Response

```json
{
  "flavor_tags": ["달콤함", "청량함", "과일향", "깔끔함", "부드러움"]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| flavor_tags | array | 맛 태그 리스트 (최대 5개) |

### curl 예시

```bash
curl -X POST http://localhost:8000/api/suggest-flavor-tags \
  -H "Content-Type: application/json" \
  -d '{
    "title": "경기도 쌀 막걸리",
    "main_ingredient": "경기도 쌀",
    "sub_ingredients": ["누룩", "물"],
    "abv_range": "5~7도"
  }'
```

### 에러 케이스
- 500: GEMINI_API_KEY가 설정되지 않은 경우 빈 배열 반환
- 500: Gemini API 호출 실패

---

## 7. POST /api/recipe/suggest-summary

레시피 정보 기반 프로젝트 요약문 자동 생성. Gemini API를 활용합니다.

### Request Body

```json
{
  "title": "경기도 쌀 막걸리",
  "main_ingredient": "경기도 쌀",
  "sub_ingredients": ["누룩", "물"],
  "abv_range": "5~7도",
  "flavor_tags": ["달콤함", "청량함"],
  "concept": null
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| title | string | O | 제목 |
| main_ingredient | string | O | 메인 재료 |
| sub_ingredients | array | X | 서브 재료 |
| abv_range | string | O | 도수 범위 |
| flavor_tags | array | X | 맛 태그 |
| concept | string/null | X | 컨셉 |

### Response

```json
{
  "summary": "경기도산 쌀을 사용하여 전통 방식으로 양조한 막걸리입니다. 5~7도의 도수로 부드러운 맛과 청량한 산미가 조화를 이룹니다. 달콤하고 깔끔한 맛으로 누구나 즐길 수 있습니다."
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| summary | string | 요약문 (3문장) |

### curl 예시

```bash
curl -X POST http://localhost:8000/api/recipe/suggest-summary \
  -H "Content-Type: application/json" \
  -d '{
    "title": "경기도 쌀 막걸리",
    "main_ingredient": "경기도 쌀",
    "sub_ingredients": ["누룩", "물"],
    "abv_range": "5~7도",
    "flavor_tags": ["달콤함", "청량함"],
    "concept": null
  }'
```

### 에러 케이스
- 500: GEMINI_API_KEY가 설정되지 않은 경우 빈 문자열 반환
- 500: Gemini API 호출 실패

---

## 8. POST /api/law/filter

레시피/펀딩 콘텐츠 법률 위반 여부 자동 검토. 3단계 필터링을 수행합니다.

### 동작 구조

1. **1단계: 키워드 1차 필터** - 명백한 위반 즉시 차단
2. **2단계: 국가법령정보센터 API** - 관련 법령 실시간 조회
3. **3단계: Gemini 분석** - 법령 조문 + 콘텐츠 분석 → 위반 여부 판단

### 검토 항목

| 항목 | 설명 |
|------|------|
| 미성년자 타겟 | 청소년, 미성년자, 학생 등 표현 |
| 불법 재료 | 메탄올, 공업용 등 금지 재료 |
| 과대광고 | 숙취 없는, 건강에 좋은, 치료 효과 등 |
| 지역특산주 요건 | 지역특산주 인증 요건 불충족 |

### Request Body

```json
{
  "content_type": "recipe",
  "title": "경기도 쌀 막걸리",
  "description": "경기도산 쌀 100% 사용, 전통 누룩으로 양조",
  "ingredients": ["쌀", "누룩", "물"],
  "target_region": "경기도"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| content_type | string | O | "recipe" 또는 "funding" |
| title | string | O | 제목 |
| description | string | O | 설명 |
| ingredients | array | X | 재료 리스트 |
| target_region | string | X | 타겟 지역 |

### Response

```json
{
  "violation": false,
  "details": [],
  "recommendation": "법적 문제가 없습니다."
}
```

위반 시:

```json
{
  "violation": true,
  "details": [
    {
      "category": "과대광고/허위표시",
      "law": "식품위생법",
      "reason": "숙취 없다는 표현은 과대광고입니다",
      "article": "식품위생법 제4조"
    }
  ],
  "recommendation": "'숙취 없는' 표현을 수정해주세요"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| violation | boolean | 위반 여부 |
| details | array | 위반 상세 정보 |
| details[].category | string | 위반 카테고리 |
| details[].law | string | 관련 법령 |
| details[].reason | string | 위반 이유 |
| details[].article | string | 관련 조문 번호 |
| recommendation | string | 수정 권장사항 |

### 예시

**위반 예시:**
```json
{
  "content_type": "recipe",
  "title": "숙취 없는 건강 막걸리",
  "description": "숙취가 전혀 없고 건강에 좋은 막걸리",
  "ingredients": ["쌀", "누룩", "물"]
}
```
→ `violation: true`

**정상 예시:**
```json
{
  "content_type": "recipe",
  "title": "경기도 쌀 막걸리",
  "description": "경기도산 쌀 100% 사용, 전통 누룩으로 양조",
  "ingredients": ["쌀", "누룩", "물"]
}
```
→ `violation: false`

### curl 예시

```bash
curl -X POST http://localhost:8000/api/law/filter \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "recipe",
    "title": "경기도 쌀 막걸리",
    "description": "경기도산 쌀 100% 사용, 전통 누룩으로 양조",
    "ingredients": ["쌀", "누룩", "물"],
    "target_region": "경기도"
  }'
```

### 에러 케이스
- 500: LAW_API_KEY 또는 GEMINI_API_KEY가 설정되지 않음
- 500: 국가법령정보센터 API 호출 실패
- 500: Gemini API 호출 실패

---

## 환경변수 설정

`.env` 파일에 다음 환경변수를 설정해야 합니다.

```bash
GEMINI_API_KEY=발급받은_Gemini_API_키
LAW_API_KEY=국가법령정보센터_API_키
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/juddam
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
PORT=8000
```

### API 키 발급

| 키 | 발급처 |
|----|--------|
| GEMINI_API_KEY | https://makersuite.google.com/app/apikey |
| LAW_API_KEY | https://www.law.go.kr/LSM/mainInfo.do |

---

## 로컬 개발 실행 방법

```bash
# 1. 가상환경 생성
python -m venv venv

# 2. 가상환경 활성화
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. 의존성 설치
pip install -r requirements.txt

# 4. .env 파일 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 5. 서버 실행
uvicorn app.main:app --reload --port 8000

# 6. Swagger UI 접속
# http://localhost:8000/docs
```

---

## 테스트

```bash
# 헬스체크
curl http://localhost:8000/health

# 술BTI 유형 판정
curl -X POST http://localhost:8000/api/survey/bti-type \
  -H "Content-Type: application/json" \
  -d '{"sweetness": 8, "body": 7, "carbonation": 3, "flavor": 4}'

# 법률 필터링
curl -X POST http://localhost:8000/api/law/filter \
  -H "Content-Type: application/json" \
  -d '{"content_type": "recipe", "title": "경기도 쌀 막걸리", "description": "경기도산 쌀 100% 사용", "ingredients": ["쌀", "누룩", "물"]}'
```
