# 주담 AI 서버 - 현재 구조 및 파일 리스트

---

## 1. 전체 구조

```
juddam-ai/
├── app/                          ← 애플리케이션 코드
│   ├── main.py                   ← FastAPI 서버 진입점
│   ├── core/                     ← 핵심 로직 (3개)
│   ├── crawler/                  ← 크롤러 (1개)
│   ├── utils/                    ← 유틸리티 (1개)
│   └── tests/                    ← 테스트 (비어있음)
└── data/                         ← 데이터
    ├── raw/                      ← 원본 데이터 (7개)
    └── processed/                ← 전처리된 데이터 (3개)
```

---

## 2. 애플리케이션 파일 (app/)

### 2.1 메인 파일

| 파일 | 역할 | 주요 기능 |
|------|------|----------|
| `main.py` | FastAPI 서버 | API 엔드포인트 5개 제공 |

**엔드포인트**:
- `GET /` - 서버 정보
- `GET /health` - 헬스체크
- `POST /api/recommend` - 맛 벡터 기반 추천
- `POST /api/taste/update` - 사용자 취향 업데이트
- `GET /api/taste/history/{user_id}` - 취향 히스토리 조회
- `POST /api/food/recommend` - 음식 기반 추천
- `POST /api/survey/convert` - 술BTI 설문 → 맛 벡터 변환

---

### 2.2 핵심 로직 (core/)

| 파일 | 역할 | 주요 기능 |
|------|------|----------|
| `recommender.py` | 추천 시스템 | 코사인 유사도, 취향 진화, 역추천 |
| `vector_extractor.py` | 맛 벡터 추출 | 텍스트 → 8차원 벡터 + 향 노트 |
| `survey_converter.py` | 설문 변환기 | 술BTI 설문 → 맛 벡터 |

**recommender.py 주요 메서드**:
- `recommend()` - 맛 벡터 기반 추천
- `recommend_by_food()` - 음식 기반 추천
- `update_user_taste()` - 사용자 취향 업데이트
- `get_evolved_taste_vector()` - 진화된 맛 벡터 계산

**vector_extractor.py 주요 메서드**:
- `extract_vector()` - 텍스트 → 8차원 맛 벡터
- `extract_notes()` - 텍스트 → 향 노트
- `process_makgeolli_data()` - 전체 데이터 처리

**survey_converter.py 주요 메서드**:
- `convert()` - 설문 응답 → 맛 벡터

---

### 2.3 크롤러 (crawler/)

| 파일 | 역할 | 주요 기능 |
|------|------|----------|
| `multi_source_crawler.py` | 다중 소스 크롤러 | 여러 사이트에서 데이터 수집 |

---

### 2.4 유틸리티 (utils/)

| 파일 | 역할 | 주요 기능 |
|------|------|----------|
| `data_preprocessor.py` | 데이터 전처리 | CSV → JSON 변환, 정제 |

---

## 3. 데이터 파일 (data/)

### 3.1 원본 데이터 (raw/)

| 파일 | 설명 | 형식 |
|------|------|------|
| `한국농수산식품유통공사_전통주정보_20241231.csv` | 전통주 정보 | CSV |
| `RT_KOREAN_LIQUOR_INFO_202407.csv` | 전통주 정보 (영문) | CSV |
| `all_tasting_notes.json` | 시음 노트 통합 | JSON |
| `dcinside_tasting_notes.json` | 디시인사이드 시음 노트 | JSON |
| `homesool_reviews.json` | 홈술 리뷰 | JSON |
| `naver_blog_makgeolli.json` | 네이버 블로그 막걸리 | JSON |
| `nongsaro_traditional_spirits.json` | 농사로 전통주 | JSON |

---

### 3.2 전처리된 데이터 (processed/)

| 파일 | 설명 | 형식 | 데이터 수 |
|------|------|------|----------|
| `makgeolli_data.json` | 기본 막걸리 데이터 | JSON | 207개 |
| `makgeolli_with_vectors.json` | 맛 벡터 포함 (구버전) | JSON | 207개 |
| `makgeolli_with_vectors_v2.json` | 맛 벡터 + 향 노트 (신버전) | JSON | 207개 |

---

## 4. 데이터 구조

### 4.1 맛 벡터 (8차원)

```json
{
  "sweetness": 1.7,        // 단맛 (0~10)
  "body": 5.0,             // 바디감 (0~10)
  "carbonation": 5.0,      // 탄산 (0~10)
  "flavor": 5.0,           // 풍미 (0~10)
  "alcohol": 5.0,          // 도수 점수 (0~10)
  "acidity": 6.4,          // 산미 (0~10)
  "aroma_intensity": 5.0,  // 향 강도 (0~10)
  "finish": 5.0            // 여운 (0~10)
}
```

### 4.2 향 노트 (4개 카테고리, 15개 세부 항목)

```json
{
  "fruit_notes": {
    "citrus": 2.0,         // 감귤류
    "berry": 0.0,          // 베리류
    "stone_fruit": 0.0,    // 핵과류
    "apple_pear": 0.0,     // 사과/배
    "tropical": 0.0,       // 열대과일
    "other_fruit": 0.0     // 기타 과일
  },
  "floral_notes": {
    "flower": 0.0,         // 꽃향
    "herbal_floral": 0.0   // 허브향
  },
  "grain_notes": {
    "rice": 2.0,           // 쌀
    "wheat": 0.0,          // 밀
    "other_grain": 2.0     // 기타 곡물
  },
  "herbal_notes": {
    "herb": 0.0,           // 허브
    "spice": 0.0,          // 스파이스
    "other_herbal": 0.0    // 기타 약초
  }
}
```

### 4.3 전체 데이터 스키마

```json
{
  "id": "makgeolli_0",
  "name": "이동 생 쌀 막걸리",
  "description": "...",
  "abv": 6.0,
  "volume": "750ml",
  "ingredients": "정제수, 백미, 팽화미, 입국, 아스파탐 등",
  "features": "적절한 산미가 음식맛을 도드라져 갈비찜과 어울린다.",
  "brewery": "이동주조",
  "region": "경기도 포천시 이동면 화동로 2466",
  "homepage": "http://edongricewine.modoo.at/",
  "awards": null,
  "taste_vector": { ... },
  "taste_notes": { ... }
}
```

---

## 5. 데이터 흐름

```
CSV (raw)
  ↓
data_preprocessor.py
  ↓
makgeolli_data.json (processed)
  ↓
vector_extractor.py
  ↓
makgeolli_with_vectors_v2.json (processed)
  ↓
recommender.py
  ↓
FastAPI (main.py)
  ↓
API 응답
```

---

## 6. 실행 방법

### 서버 실행
```bash
uvicorn app.main:app --reload --port 8000
```

### 데이터 전처리
```bash
python app/utils/data_preprocessor.py
```

### 맛 벡터 추출
```bash
python app/core/vector_extractor.py
```

### 추천 시스템 테스트
```bash
python app/core/recommender.py
```

---

## 7. 현재 상태

| 항목 | 상태 |
|------|------|
| 데이터 수집 | ✅ 완료 (207개) |
| 데이터 전처리 | ✅ 완료 |
| 맛 벡터 추출 | ✅ 완료 (8차원 + 향 노트) |
| 추천 시스템 | ✅ 완료 (코사인 + 취향 진화 + 역추천) |
| FastAPI 서버 | ✅ 완료 (5개 엔드포인트) |
| 설문 변환기 | ✅ 완료 |
| 법률 필터링 | ❌ 미구현 |
| RAG DB | ❌ 미구현 |
| 인사이트 대시보드 | ❌ 미구현 |
| DB 연동 | ❌ 미구현 |

---

## 8. 수정 가능한 부분

### 8.1 맛 벡터 수정
- **파일**: `app/core/vector_extractor.py`
- **수정 대상**: 키워드 사전, 점수 계산 로직
- **재추출**: `python app/core/vector_extractor.py`

### 8.2 데이터 직접 수정
- **파일**: `data/processed/makgeolli_with_vectors_v2.json`
- **수정 대상**: 특정 막걸리의 `taste_vector`, `taste_notes`

### 8.3 추천 로직 수정
- **파일**: `app/core/recommender.py`
- **수정 대상**: 유사도 계산, 가중치, 취향 진화 로직

---

## 9. 파일 총 개수

| 폴더 | 파일 수 |
|------|--------|
| app/ | 9개 |
| data/raw/ | 7개 |
| data/processed/ | 3개 |
| **총계** | **19개** |
