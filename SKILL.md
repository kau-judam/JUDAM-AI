# 주담 AI 서버 — Claude Code 스킬 (피드백 반영 고도화 버전)
# 최종 업데이트: 2026-04-27 / 중간 발표 피드백 반영

## 프로젝트 개요
- 서비스명: 酒談 (주담) — 소비자 맞춤형 전통주 공동 기획 펀딩 플랫폼
- AI 파트 담당: 황주원
- 스택: Python 3.12 + FastAPI + scikit-learn + Gemini API
- 서버 위치: juddam-ai/ 폴더

## 핵심 설계 원칙 (발표 피드백 반영)

### 원칙 1: 라벨링 신뢰도 확보 (피드백 1 대응)
Gemini 단독 라벨링의 주관성 문제를 앙커링 + 크라우드소싱으로 해결.
- 앙커 데이터 10~20개: 실제 시음 후 직접 점수 매긴 기준 데이터
- 앙커를 Gemini 프롬프트에 포함시켜 일관성 확보
- 서비스 오픈 후 실제 사용자 평가로 자동 보정

### 원칙 2: 추천 차별성 확보 (피드백 2 대응)
단순 코사인 유사도를 넘어서는 차별화 3가지:
- 취향 진화 트래킹: 술 기록마다 맛 벡터 자동 업데이트
- 컨텍스트 기반 추천: 계절/날씨/상황 반영
- 역추천: 음식/안주 기반으로 어울리는 전통주 추천

### 원칙 3: 도메인 전문성 확보 (피드백 3 대응)
Gemini 단독 의존 금지. 전통주 RAG DB 구축 후 함께 활용.
- RAG 소스: 전통주갤러리, 더술닷컴 리뷰, 농촌진흥청 자료
- 법률 필터링: 국가법령정보센터 API 실시간 조회 + Gemini

### 원칙 4: 예측 로직 구체화 (피드백 4 대응)
단순 집계(평균)와 예측(미래값 추정)을 명확히 분리.
- 집계: Pandas로 현재 통계 계산
- 예측: Holt-Winters 지수평활법으로 트렌드 예측
- 군집화: K-Means로 레시피 수요 패턴 파악

## 폴더 구조
```
juddam-ai/
├── app/
│   ├── main.py              ← FastAPI 진입점
│   ├── recommend.py         ← 술BTI 추천 (코사인 + 컨텍스트 + 협업 필터링)
│   ├── vector_validator.py  ← 설문 응답 → 맛 벡터 변환 및 검증
│   ├── filter.py            ← 법률 필터링 (국가법령정보센터 API + Gemini)
│   ├── insight.py           ← 인사이트 대시보드 (집계 + 예측 + 군집화)
│   ├── rag.py               ← 전통주 RAG DB 구축 및 검색
│   ├── auto_pipeline.py     ← 신규 전통주 자동 맛 벡터 생성
│   ├── db.py                ← DB 연결 (asyncpg)
│   └── models.py            ← Pydantic 모델
├── data/
│   ├── raw/                 ← 원본 CSV
│   ├── processed/           ← 전처리된 데이터
│   └── anchors.json         ← 앙커 데이터 (직접 시음한 기준점 10~20개)
├── models/
│   ├── taste_model.pkl      ← 학습된 맛 예측 모델
│   └── vectorizer.pkl       ← TF-IDF 벡터라이저
├── rag_db/                  ← 전통주 전문 문서 벡터 DB
├── .env
└── requirements.txt
```

## 핵심 개념

### 술BTI 맛 벡터
5개 축: sweetness(단맛), body(바디감), carbonation(탄산), flavor(풍미), alcohol(도수)
각 축: 0~10 사이 float 값
예시: {"sweetness": 7.5, "body": 4.0, "carbonation": 8.0, "flavor": 6.5, "alcohol": 3.0}

### 앙커 데이터 구조
```json
{
  "anchors": [
    {
      "name": "복순도가 복분자주",
      "sweetness": 8.0, "body": 5.0, "carbonation": 2.0,
      "flavor": 9.0, "alcohol": 7.0,
      "note": "실제 시음 기반"
    }
  ]
}
```

### RAG 검색 방식
전통주 전문 문서 → TF-IDF 벡터화 → 코사인 유사도 검색
관련 문서 3~5개를 Gemini 프롬프트에 포함시켜 전달

### 인사이트 예측 vs 집계 구분
- 집계 (현재): Pandas groupby, mean, std
- 예측 (미래): statsmodels ExponentialSmoothing (Holt-Winters)
- 군집화 (패턴): sklearn KMeans + TF-IDF

## 코드 작성 규칙
1. 모든 함수에 한국어 docstring 필수
2. 타입 힌트 반드시 작성
3. 에러 처리 항상 포함 (try/except + logging)
4. 환경변수는 .env에서 load_dotenv()로 로드
5. DB 연결은 asyncpg 사용 (비동기)
6. Pydantic 모델로 요청/응답 검증
7. 외부 API 호출은 재시도 로직 포함 (최대 3회)
8. 캐싱은 Redis 사용 (응답 속도 향상)
