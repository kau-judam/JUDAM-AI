# 4팀 [칭찬해주] 상세개발계획서 - AI 파트 분석

---

## 1. 엑셀 파일 구조

### 1.1 전체 구조

| 열 | 설명 |
|----|------|
| Task | 작업 분류 |
| Detail | 상세 작업 내용 |
| 담당자 | 담당자 |
| 3주 | 3주차 진행 상황 |
| 4주 | 4주차 진행 상황 |
| 5주 | 5주차 진행 상황 |
| 6주 | 6주차 진행 상황 |
| Issues | 이슈 사항 |

### 1.2 AI 파트 작업 목록

| 작업 | 상세 내용 | 담당자 | 3주 | 4주 | 5주 | 6주 | 상태 |
|------|----------|--------|-----|-----|-----|-----|------|
| API 명세서 작성 | AI 서비스 API 명세서 작성 | AI | 진행중 | 완료 | | | ✅ 완료 |
| 환경 구축 | FastAPI 개발 환경 구축 및 기본 설정 | AI | 진행중 | 완료 | | | ✅ 완료 |
| API 키 발급 | Gemini API 키 발급 및 테스트 | AI | 진행중 | 완료 | | | ✅ 완료 |
| 맛 데이터 DB 구축 | 맛 데이터 DB 구축 (CSV 파싱 + 맛 벡터 라벨링) | AI | 진행중 | 완료 | | | ✅ 완료 |
| 술BTI 설문 | 술BTI 설문 문항 작성 (6문항 작성) | AI | | 진행중 | 완료 | | ✅ 완료 |
| 추천 알고리즘 | 추천 알고리즘 구현 (코사인 유사도) | AI | | 진행중 | 완료 | | ✅ 완료 |
| 통신 테스트 | Node.js ↔ FastAPI HTTP 통신 테스트 | AI | | | 진행중 | 완료 | | ⏳ 미완료 |
| 전체 테스트 | 전체 AI 기능 테스트 및 통합 | AI | | | | 진행중 | ⏳ 미완료 |

---

## 2. 현재 AI 파트 개발 상황

### 2.1 완료된 작업 ✅

| 작업 | 완료 내용 | 파일 |
|------|----------|------|
| API 명세서 작성 | FastAPI 엔드포인트 5개 구현 | `app/main.py` |
| 환경 구축 | Python 3.12 + FastAPI 환경 구축 | `app/main.py` |
| API 키 발급 | Gemini API 키 발급 및 테스트 | `.env` |
| 맛 데이터 DB 구축 | 207개 막걸리 데이터, 8차원 벡터 + 향 노트 | `data/processed/makgeolli_with_vectors_v2.json` |
| 술BTI 설문 | 설문 응답 → 맛 벡터 변환 로직 구현 | `app/core/survey_converter.py` |
| 추천 알고리즘 | 코사인 유사도 + 취향 진화 + 역추천 구현 | `app/core/recommender.py` |

### 2.2 미완료된 작업 ⏳

| 작업 | 미완료 내용 | 우선순위 |
|------|----------|----------|
| Node.js ↔ FastAPI 통신 테스트 | 백엔드와 연동 테스트 | 높음 |
| 전체 AI 기능 테스트 | 통합 테스트 | 높음 |
| 법률 필터링 구현 | 국가법령정보센터 API 연동 | 중간 |
| RAG DB 구축 | 전통주 전문 문서 벡터화 | 중간 |
| 인사이트 대시보드 | 집계 + 예측 + 군집화 | 낮음 |
| DB 연동 | PostgreSQL + Redis 연결 | 높음 |

---

## 3. 엑셀 파일 수정 필요 사항

### 3.1 AI 파트 작업 상태 업데이트

| 작업 | 현재 상태 | 수정 필요 사항 |
|------|----------|----------------|
| API 명세서 작성 | ✅ 완료 | FastAPI 자동 문서화 URL 추가 |
| 환경 구축 | ✅ 완료 | 서버 실행 명령어 추가 |
| API 키 발급 | ✅ 완료 | API 키 발급 방법 추가 |
| 맛 데이터 DB 구축 | ✅ 완료 | 데이터 구조 설명 추가 |
| 술BTI 설문 | ✅ 완료 | 설문 문항 추가 |
| 추천 알고리즘 | ✅ 완료 | 알고리즘 설명 추가 |
| 통신 테스트 | ⏳ 미완료 | 백엔드 연동 방법 추가 |
| 전체 테스트 | ⏳ 미완료 | 테스트 계획 추가 |

### 3.2 추가 필요 작업

| 작업 | 설명 | 우선순위 |
|------|------|----------|
| DB 연동 | PostgreSQL + Redis 연결 | 높음 |
| 법률 필터링 구현 | 국가법령정보센터 API 연동 | 중간 |
| RAG DB 구축 | 전통주 전문 문서 벡터화 | 중간 |
| 인사이트 대시보드 | 집계 + 예측 + 군집화 | 낮음 |
| 앙커 데이터 구축 | 실제 시음 기반 10~20개 기준점 | 중간 |

---

## 4. API 명세서 (FastAPI 자동 문서화)

### 4.1 서버 정보

- **서버 주소**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 4.2 엔드포인트 목록

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/` | GET | 서버 정보 |
| `/health` | GET | 헬스체크 |
| `/api/recommend` | POST | 맛 벡터 기반 추천 |
| `/api/taste/update` | POST | 사용자 취향 업데이트 |
| `/api/taste/history/{user_id}` | GET | 취향 히스토리 조회 |
| `/api/food/recommend` | POST | 음식 기반 추천 |
| `/api/survey/convert` | POST | 술BTI 설문 → 맛 벡터 변환 |

### 4.3 요청/응답 예시

#### 4.3.1 술BTI 설문 → 맛 벡터 변환

**요청**:
```json
{
  "sweetness": 7,
  "body": 5,
  "carbonation": 3,
  "flavor": 6,
  "alcohol": 4
}
```

**응답**:
```json
{
  "status": "success",
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
```

#### 4.3.2 맛 벡터 기반 추천

**요청**:
```json
{
  "user_vector": {
    "sweetness": 7.0,
    "body": 5.0,
    "carbonation": 3.0,
    "flavor": 6.0,
    "alcohol": 4.0,
    "acidity": 5.0,
    "aroma_intensity": 5.0,
    "finish": 5.0
  },
  "top_k": 10,
  "exclude_ids": []
}
```

**응답**:
```json
[
  {
    "id": "makgeolli_0",
    "name": "이동 생 쌀 막걸리",
    "similarity": 0.95,
    "abv": 6.0,
    "brewery": "이동주조",
    "region": "경기도 포천시 이동면 화동로 2466",
    "features": "적절한 산미가 음식맛을 도드라져 갈비찜과 어울린다.",
    "taste_vector": {
      "sweetness": 1.7,
      "body": 5.0,
      "carbonation": 5.0,
      "flavor": 5.0,
      "alcohol": 5.0,
      "acidity": 6.4,
      "aroma_intensity": 5.0,
      "finish": 5.0
    }
  }
]
```

---

## 5. Node.js ↔ FastAPI 통신 방식

### 5.1 통신 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                     프론트엔드 (React)                    │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP
┌────────────────────▼────────────────────────────────────┐
│              백엔드 (Node.js + Express)                   │
│  - 사용자 인증 (JWT)                                      │
│  - 커뮤니티 CRUD                                         │
│  - 펀딩 CRUD                                             │
│  - AI 서비스 프록시                                       │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP
┌────────────────────▼────────────────────────────────────┐
│              AI 서비스 (FastAPI)                          │
│  - 술BTI 설문 → 맛 벡터 변환                             │
│  - 맛 벡터 기반 추천                                     │
│  - 취향 진화 트래킹                                      │
│  - 음식 기반 역추천                                      │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Node.js 코드 예시

```javascript
const axios = require('axios');

// AI 서비스 기본 URL
const AI_SERVICE_URL = 'http://localhost:8000';

// 술BTI 설문 → 맛 벡터 변환
async function convertSurveyToVector(surveyResponse) {
  try {
    const response = await axios.post(`${AI_SERVICE_URL}/api/survey/convert`, surveyResponse);
    return response.data.taste_vector;
  } catch (error) {
    console.error('술BTI 설문 변환 오류:', error);
    throw error;
  }
}

// 맛 벡터 기반 추천
async function getRecommendations(tasteVector, topK = 10, excludeIds = []) {
  try {
    const response = await axios.post(`${AI_SERVICE_URL}/api/recommend`, {
      user_vector: tasteVector,
      top_k: topK,
      exclude_ids: excludeIds
    });
    return response.data;
  } catch (error) {
    console.error('추천 오류:', error);
    throw error;
  }
}

// 사용자 취향 업데이트
async function updateUserTaste(userId, drinkId, rating, tags = []) {
  try {
    const response = await axios.post(`${AI_SERVICE_URL}/api/taste/update`, {
      user_id: userId,
      drink_id: drinkId,
      rating: rating,
      tags: tags
    });
    return response.data;
  } catch (error) {
    console.error('취향 업데이트 오류:', error);
    throw error;
  }
}

// 취향 히스토리 조회
async function getTasteHistory(userId) {
  try {
    const response = await axios.get(`${AI_SERVICE_URL}/api/taste/history/${userId}`);
    return response.data;
  } catch (error) {
    console.error('취향 히스토리 조회 오류:', error);
    throw error;
  }
}

// 음식 기반 추천
async function getFoodRecommendations(food, topK = 5) {
  try {
    const response = await axios.post(`${AI_SERVICE_URL}/api/food/recommend`, {
      food: food,
      top_k: topK
    });
    return response.data;
  } catch (error) {
    console.error('음식 기반 추천 오류:', error);
    throw error;
  }
}

// AI 서비스 헬스체크
async function checkAIServiceHealth() {
  try {
    const response = await axios.get(`${AI_SERVICE_URL}/health`);
    return response.data;
  } catch (error) {
    console.error('AI 서비스 헬스체크 오류:', error);
    throw error;
  }
}

// 사용 예시
async function main() {
  try {
    // AI 서비스 헬스체크
    const health = await checkAIServiceHealth();
    console.log('AI 서비스 상태:', health);

    // 술BTI 설문 → 맛 벡터 변환
    const surveyResponse = {
      sweetness: 7,
      body: 5,
      carbonation: 3,
      flavor: 6,
      alcohol: 4
    };
    const tasteVector = await convertSurveyToVector(surveyResponse);
    console.log('맛 벡터:', tasteVector);

    // 맛 벡터 기반 추천
    const recommendations = await getRecommendations(tasteVector, 5);
    console.log('추천 결과:', recommendations);

    // 사용자 취향 업데이트
    await updateUserTaste('user_1', 'makgeolli_0', 5, ['달콤', '산미']);

    // 취향 히스토리 조회
    const history = await getTasteHistory('user_1');
    console.log('취향 히스토리:', history);

    // 음식 기반 추천
    const foodRecommendations = await getFoodRecommendations('갈비찜', 3);
    console.log('음식 기반 추천:', foodRecommendations);

  } catch (error) {
    console.error('오류:', error);
  }
}

main();
```

---

## 6. 다음 단계

### 6.1 엑셀 파일 수정

1. **AI 파트 작업 상태 업데이트**: 완료된 작업 표시
2. **API 명세서 추가**: FastAPI 자동 문서화 URL 추가
3. **통신 방식 추가**: Node.js ↔ FastAPI 통신 방식 명시
4. **테스트 계획 추가**: 단위/통합/시스템 테스트 계획

### 6.2 SRD 작성

1. **기능 요구사항 작성**: AI 서비스 기능 명세
2. **비기능 요구사항 작성**: 성능, 보안, 가용성, 확장성
3. **API 명세서 작성**: 모든 API의 요청/응답 형식 명시
4. **데이터베이스 설계**: AI 서비스 DB 스키마 정의

### 6.3 개발 진행

1. **Node.js ↔ FastAPI 통신 테스트**: 백엔드와 연동
2. **전체 AI 기능 테스트**: 통합 테스트
3. **DB 연동**: PostgreSQL + Redis 연결
4. **법률 필터링 구현**: 국가법령정보센터 API 연동

---

어떤 작업부터 진행할까요?

1. **엑셀 파일 수정**: 개발 계획서 업데이트
2. **SRD 작성**: 전체 요구사항 문서 작성
3. **Node.js ↔ FastAPI 통신 테스트**: 백엔드와 연동
4. **DB 연동**: PostgreSQL + Redis 연결
