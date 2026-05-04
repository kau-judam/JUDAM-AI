# 주담 AI 서버

소비자 맞춤형 전통주 공동 기획 펀딩 플랫폼 "주담"의 AI 서버

## 프로젝트 개요

- **서비스명**: 酒談 (주담)
- **목적**: 소비자 취향 기반 전통주 추천 및 법률 필터링
- **기술 스택**: Python 3.12 + FastAPI + scikit-learn + Gemini API
- **담당**: AI 파트 (황주원)

## 주요 기능

- **술BTI 추천**: 맛 벡터 기반 코사인 유사도 추천
- **취향 진화**: 사용자 평가로 맛 벡터 자동 업데이트
- **법률 필터링**: 청소년보호법, 식품위생법, 자본시장법 등 실시간 검사
- **인사이트 대시보드**: 집계 + 예측 + 군집화
- **RAG 검색**: 전통주 전문 문서 기반 검색

## 프로젝트 구조

```
juddam-ai/
├── app/
│   ├── main.py              # FastAPI 진입점
│   ├── models.py            # Pydantic 모델
│   ├── db.py                # DB 연결 (asyncpg)
│   ├── filter.py            # 법률 필터링 (국가법령정보센터 API + Gemini)
│   ├── insight.py           # 인사이트 대시보드 (집계 + 예측 + 군집화)
│   ├── rag.py               # 전통주 RAG DB
│   ├── auto_pipeline.py     # 신규 전통주 자동 맛 벡터 생성
│   ├── core/
│   │   ├── recommender.py   # 술BTI 추천 (코사인 + 컨텍스트 + 협업 필터링)
│   │   ├── survey_converter.py  # 설문 응답 → 맛 벡터 변환
│   │   └── vector_extractor.py  # 고도화된 맛 벡터 추출
│   ├── crawler/
│   │   └── multi_source_crawler.py  # 다중 소스 크롤러
│   └── utils/
│       └── data_preprocessor.py  # 데이터 전처리
├── data/
│   ├── raw/                 # 원본 CSV
│   ├── processed/           # 전처리된 데이터
│   └── anchors.json         # 앙커 데이터 (실제 시음 기반)
├── rag_db/                  # 전통주 전문 문서 벡터 DB
├── .env                     # 환경변수 (절대 커밋 금지)
├── .env.example             # 환경변수 예시
├── requirements.txt         # 의존성 패키지
├── SKILL.md                 # AI 서버 설계 원칙
├── PROMPTS.md               # 단계별 개발 프롬프트
└── CLAUDE.md                # Claude Code 설정
```

## 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 실제 API 키 입력
```

## 실행

```bash
# 서버 실행
uvicorn app.main:app --reload --port 8000

# API 문서
http://localhost:8000/docs
```

## API 엔드포인트

### 추천
- `POST /api/recommend` - 맛 벡터 기반 추천
- `POST /api/taste/update` - 사용자 취향 업데이트
- `GET /api/taste/history/{user_id}` - 사용자 취향 히스토리 조회
- `POST /api/food/recommend` - 음식 기반 추천

### 설문
- `POST /api/survey/convert` - 술BTI 설문 → 맛 벡터 변환

### 법률 필터링
- `POST /api/law/filter` - 법률 필터링
- `GET /api/law/traditional-alcohol` - 전통주 관련 주요 법률

### 인사이트
- `GET /api/insight` - 인사이트 대시보드

### RAG
- `POST /api/rag/search` - RAG 문서 검색
- `GET /api/rag/category/{category}` - 카테고리별 문서 조회

### 헬스체크
- `GET /health` - 서버 상태 확인

## 개발 순서

1. 8주차: CSV 파싱 → Gemini 라벨링 → 자체 모델 학습
2. 8~9주차: 코사인 유사도 추천 API
3. 9주차: 술BTI 문항 확정 → 벡터 변환 로직
4. 10주차: 법률 필터링 + 인사이트 대시보드
5. 11주차~: 임베딩 고도화 + 하이브리드 추천

## 환경변수

```env
GEMINI_API_KEY=발급받은키
LAW_API_KEY=국가법령정보센터키
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/juddam
REDIS_URL=redis://localhost:6379
```

## 테스트

```bash
# 테스트 실행
pytest tests/ -v
```

## 주의사항

- .env 파일은 절대 커밋하지 마세요
- 앙커 데이터는 실제 시음 기반으로 입력해야 합니다
- 외부 API 호출은 Mock 테스트 먼저 진행하세요

## 백엔드 연동

백엔드 Node.js 서버와의 연동 방법은 [BACKEND_INTEGRATION.md](BACKEND_INTEGRATION.md)를 참고하세요.

### 연동 방식
- **공유 DB 방식**: 백엔드와 AI 서버가 동일한 PostgreSQL DB 공유
- **API 통신**: 백엔드가 AI 서버 API 호출

### 데이터베이스 구조
- `users`: 사용자 정보
- `drinks`: 전통주 정보 (맛 벡터 포함)
- `user_taste_history`: 취향 히스토리
- `recommendations`: 추천 기록
- `food_pairings`: 음식 페어링

## AWS 배포

AWS EC2 배포 방법은 [DEPLOYMENT.md](DEPLOYMENT.md)를 참고하세요.

### 배포 구성
- **EC2**: Ubuntu 22.04 LTS, t3.medium 이상
- **RDS**: PostgreSQL 15.x
- **ElastiCache**: Redis (선택사항)
- **Nginx**: 리버스 프록시
- **Supervisor**: 프로세스 관리

### 예상 비용
- EC2: 약 $30/월
- RDS: 약 $15/월
- ElastiCache: 약 $20/월
- **합계**: 약 $65/월

## 문서

- [API_GUIDE.md](API_GUIDE.md) - API 상세 가이드
- [BACKEND_INTEGRATION.md](BACKEND_INTEGRATION.md) - 백엔드 연동 가이드
- [DEPLOYMENT.md](DEPLOYMENT.md) - AWS 배포 가이드
- [SKILL.md](SKILL.md) - AI 서버 설계 원칙
- [CLAUDE.md](CLAUDE.md) - Claude Code 설정
