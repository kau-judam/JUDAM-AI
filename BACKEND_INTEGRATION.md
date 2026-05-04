# 백엔드 연동 가이드

주담 AI 서버와 백엔드 Node.js 서버 연동 방법

## 아키텍처 개요

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Frontend      │         │   Backend       │         │   AI Server     │
│   (React/Vue)   │◄────────►│   (Node.js)     │◄────────►│   (Python)      │
│                 │         │                 │         │   FastAPI       │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                    │
                                    ▼
                            ┌─────────────────┐
                            │   PostgreSQL    │
                            │   (공유 DB)      │
                            └─────────────────┘
```

## 데이터베이스 구조

### 테이블 스키마

#### users (사용자)
```sql
CREATE TABLE users (
    id VARCHAR(50) PRIMARY KEY,           -- 사용자 ID
    name VARCHAR(100),                    -- 이름
    email VARCHAR(100),                   -- 이메일
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### drinks (전통주)
```sql
CREATE TABLE drinks (
    id VARCHAR(50) PRIMARY KEY,           -- 전통주 ID
    name VARCHAR(100) NOT NULL,           -- 이름
    abv FLOAT,                            -- 알콜 도수 (%)
    brewery VARCHAR(100),                 -- 양조장
    region VARCHAR(50),                   -- 지역
    description TEXT,                     -- 설명
    features TEXT,                        -- 특징
    ingredients TEXT,                     -- 재료
    awards TEXT,                          -- 수상 이력
    taste_vector JSONB,                   -- 맛 벡터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### user_taste_history (취향 히스토리)
```sql
CREATE TABLE user_taste_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    drink_id VARCHAR(50) REFERENCES drinks(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),  -- 별점 (1~5)
    tags TEXT[],                          -- 태그
    taste_vector JSONB,                   -- 평가 시 맛 벡터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### recommendations (추천 기록)
```sql
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    drink_id VARCHAR(50) REFERENCES drinks(id) ON DELETE CASCADE,
    similarity FLOAT,                     -- 유사도 점수
    context JSONB,                        -- 추천 컨텍스트
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### food_pairings (음식 페어링)
```sql
CREATE TABLE food_pairings (
    id SERIAL PRIMARY KEY,
    food_name VARCHAR(100) NOT NULL,      -- 음식 이름
    drink_id VARCHAR(50) REFERENCES drinks(id) ON DELETE CASCADE,
    reason TEXT,                          -- 페어링 이유
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 맛 벡터 구조 (JSONB)

```json
{
  "sweetness": 7.5,        // 단맛 (0~10)
  "body": 4.0,            // 바디감 (0~10)
  "carbonation": 8.0,     // 탄산 (0~10)
  "flavor": 6.5,          // 풍미 (0~10)
  "alcohol": 3.0,         // 도수 (0~10)
  "acidity": 5.0,         // 산미 (0~10)
  "aroma_intensity": 7.0, // 향기 강도 (0~10)
  "finish": 4.5           // 여운 (0~10)
}
```

## 연동 방식

### 1. 공유 데이터베이스 방식 (권장)

백엔드와 AI 서버가 동일한 PostgreSQL DB를 공유합니다.

#### 장점
- 데이터 일관성 보장
- 실시간 동기화 불필요
- 트랜잭션 처리 가능

#### 설정

**백엔드 (Node.js)**
```javascript
// .env
DATABASE_URL=postgresql://user:pass@localhost:5432/juddam
AI_SERVER_URL=http://localhost:8000
```

**AI 서버 (Python)**
```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/juddam
```

### 2. API 통신 방식

백엔드가 AI 서버의 API를 호출하여 결과를 받습니다.

#### 추천 API 호출 예시

```javascript
// 백엔드 서버에서
const response = await fetch(`${process.env.AI_SERVER_URL}/api/recommend`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_vector: user.tasteVector,
    top_k: 10,
    exclude_ids: user.viewedDrinkIds
  })
});

const recommendations = await response.json();

// 결과를 DB에 저장
await db.recommendations.create({
  user_id: user.id,
  drink_id: recommendations[0].id,
  similarity: recommendations[0].similarity
});
```

## 백엔드 구현 예시

### 사용자 취향 업데이트

```javascript
// POST /api/users/:userId/taste
router.post('/users/:userId/taste', async (req, res) => {
  const { userId } = req.params;
  const { drinkId, rating, tags } = req.body;

  try {
    // 1. AI 서버에 취향 업데이트 요청
    await fetch(`${process.env.AI_SERVER_URL}/api/taste/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        drink_id: drinkId,
        rating,
        tags
      })
    });

    // 2. DB에 기록 저장
    await db.userTasteHistory.create({
      user_id: userId,
      drink_id: drinkId,
      rating,
      tags
    });

    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

### 법률 필터링

```javascript
// POST /api/recipes
router.post('/recipes', async (req, res) => {
  const { title, description, ingredients, content_type } = req.body;

  try {
    // 1. AI 서버로 법률 필터링 요청
    const filterResponse = await fetch(`${process.env.AI_SERVER_URL}/api/law/filter`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content_type: content_type || 'recipe',
        title,
        description,
        ingredients,
        target_region: req.body.target_region
      })
    });

    const filterResult = await filterResponse.json();

    // 2. 위반 시 에러 반환
    if (filterResult.violation) {
      return res.status(400).json({
        error: '법적 문제가 있습니다',
        details: filterResult.details,
        recommendation: filterResult.recommendation
      });
    }

    // 3. 정상 시 레시피 저장
    const recipe = await db.recipes.create({
      title,
      description,
      ingredients,
      user_id: req.user.id
    });

    res.json(recipe);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

### 설문 응답 처리

```javascript
// POST /api/survey
router.post('/survey', async (req, res) => {
  const surveyData = req.body;

  try {
    // 1. AI 서버로 설문 변환 요청
    const response = await fetch(`${process.env.AI_SERVER_URL}/api/survey/convert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(surveyData)
    });

    const result = await response.json();

    // 2. 사용자 맛 벡터 업데이트
    await db.users.update(req.user.id, {
      taste_vector: result.taste_vector
    });

    // 3. 초기 추천 요청
    const recommendResponse = await fetch(`${process.env.AI_SERVER_URL}/api/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_vector: result.taste_vector,
        top_k: 10
      })
    });

    const recommendations = await recommendResponse.json();

    res.json({
      taste_vector: result.taste_vector,
      recommendations
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

## 데이터 동기화

### 전통주 데이터 동기화

백엔드에서 새로운 전통주가 추가되면 AI 서버에도 동기화해야 합니다.

```javascript
// 전통주 생성 시
router.post('/drinks', async (req, res) => {
  const drinkData = req.body;

  try {
    // 1. DB에 저장
    const drink = await db.drinks.create(drinkData);

    // 2. AI 서버에 알림 (선택사항 - 실시간 추천에 필요)
    await fetch(`${process.env.AI_SERVER_URL}/api/drinks/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: drink.id,
        name: drink.name,
        abv: drink.abv,
        brewery: drink.brewery,
        region: drink.region,
        features: drink.features,
        taste_vector: drink.taste_vector
      })
    });

    res.json(drink);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

## 에러 처리

### AI 서버 다운 시 대응

```javascript
async function callAIServer(endpoint, data) {
  try {
    const response = await fetch(`${process.env.AI_SERVER_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      timeout: 5000  // 5초 타임아웃
    });

    if (!response.ok) {
      throw new Error(`AI Server error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('AI Server call failed:', error);

    // 폴백 로직
    return getFallbackRecommendation(data);
  }
}

function getFallbackRecommendation(data) {
  // 기본 추천 로직 (인기 전통주 등)
  return db.drinks.findAll({
    order: [['rating', 'DESC']],
    limit: 10
  });
}
```

## 환경변수

### 백엔드 (.env)
```env
# 데이터베이스
DATABASE_URL=postgresql://user:pass@localhost:5432/juddam

# AI 서버
AI_SERVER_URL=http://localhost:8000
AI_SERVER_TIMEOUT=5000

# Redis (캐싱)
REDIS_URL=redis://localhost:6379
```

### AI 서버 (.env)
```env
# 데이터베이스
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/juddam

# 외부 API
GEMINI_API_KEY=your_gemini_api_key
LAW_API_KEY=your_law_api_key

# Redis
REDIS_URL=redis://localhost:6379

# 서버 설정
HOST=0.0.0.0
PORT=8000
```

## 테스트

### 로컬 개발 환경

```bash
# 1. PostgreSQL 시작
docker run -d --name juddam-db \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=juddam \
  -p 5432:5432 postgres:15

# 2. Redis 시작
docker run -d --name juddam-redis -p 6379:6379 redis:7

# 3. 백엔드 시작
cd backend
npm install
npm run dev

# 4. AI 서버 시작
cd ai-server
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 모니터링

### 헬스체크

```javascript
// 주기적 헬스체크
setInterval(async () => {
  try {
    const response = await fetch(`${process.env.AI_SERVER_URL}/health`);
    const health = await response.json();

    if (health.status !== 'ok') {
      console.warn('AI Server health check failed:', health);
      // 알림 발송
    }
  } catch (error) {
    console.error('AI Server is down:', error);
  }
}, 60000);  // 1분마다
```
