# 주담 AI 서버

소비자 맞춤형 전통주 공동 기획 펀딩 플랫폼 "주담"의 AI 서버

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 서비스명 | 酒談 (주담) |
| 목적 | 소비자 취향 기반 전통주 추천 · 법률 필터링 · 양조장 인사이트 |
| 기술 스택 | Python 3.12 + FastAPI + scikit-learn + Gemini 2.5 Flash Lite |
| AI 모델 | gemini-2.5-flash-lite (추천/채팅/레시피/법률/인사이트) |
| 데이터 | 전통주 207종 맛 벡터 (8축) |
| 담당 | AI 파트 (황주원) |

## 주요 기능

| 기능 | 설명 |
|------|------|
| **술BTI 추천** | 25문항 설문 → 8축 맛 벡터 → 코사인 유사도 추천 + match_reason |
| **취향 진화 트래킹** | 축별 평가(ratings) 누적 → 맛 벡터 자동 진화 |
| **전통주 채팅** | Gemini 기반 전통주 전문 Q&A + 후속 질문 추천 |
| **레시피 AI** | 서브재료 추천 · 맛 태그 생성 · 요약문 자동 생성 |
| **법률 필터링** | 청소년보호법 · 식품위생법 · 자본시장법 실시간 검사 (3단계) |
| **인사이트 대시보드** | 집계 + 예측 + 군집화 + Gemini AI 리포트 |
| **크롤러 모니터** | koreansool.co.kr 신규 전통주 자동 감지 + 맛 벡터 생성 |
| **전통주 등록 요청** | 사용자 등록 요청 접수 → 관리자 승인 → 맛 벡터 자동 생성 |

## 프로젝트 구조

```
juddam-ai/
├── app/
│   ├── main.py              # FastAPI 진입점 (전체 라우터)
│   ├── models.py            # Pydantic 요청/응답 모델
│   ├── db.py                # DB 연결 (asyncpg)
│   ├── chat.py              # 전통주 전문 채팅 API
│   ├── insight.py           # 인사이트 대시보드 + Gemini AI 리포트
│   ├── law_client.py        # 법률 필터링 (국가법령정보센터 + Gemini)
│   ├── rag.py               # 전통주 RAG 문서 검색
│   ├── recipe.py            # 레시피 AI (서브재료/맛태그/요약문)
│   ├── auto_pipeline.py     # 신규 전통주 자동 맛 벡터 생성 (Gemini 2.5 Flash Lite)
│   ├── core/
│   │   ├── recommender.py       # 추천 엔진 (코사인 유사도 + 취향 진화)
│   │   ├── survey_converter.py  # 25문항 설문 → 8축 맛 벡터 변환
│   │   └── vector_extractor.py  # 맛 벡터 추출
│   └── crawler/
│       ├── __init__.py
│       └── traditional_alcohol_monitor.py  # koreansool.co.kr 크롤러
├── data/
│   ├── raw/                     # 원본 CSV
│   ├── processed/               # 전처리된 데이터 (makgeolli_with_vectors.json)
│   └── crawler_seen.json        # 크롤러 중복 방지 캐시
├── .env                         # 환경변수 (절대 커밋 금지)
├── .env.example                 # 환경변수 예시
├── requirements.txt             # 의존성 패키지
├── API_GUIDE.md                 # API 상세 가이드
├── DEPLOYMENT.md                # AWS 배포 가이드
├── SKILL.md                     # AI 서버 설계 원칙
└── CLAUDE.md                    # Claude Code 설정
```

## 맛 벡터 8축

| 축 | 설명 | 범위 |
|----|------|------|
| sweetness | 단맛 | 0~10 |
| body | 바디감 | 0~10 |
| carbonation | 탄산 | 0~10 |
| flavor | 풍미 | 0~10 |
| alcohol | 도수감 | 0~10 |
| acidity | 산미 | 0~10 |
| aroma_intensity | 향기 강도 | 0~10 |
| finish | 여운 | 0~10 |

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

# API 문서 (Swagger UI)
http://localhost:8000/docs
```

## API 엔드포인트 요약

### 헬스체크
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 · API별 동작 여부 확인 |

### 추천
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/recommend` | 맛 벡터 기반 추천 (match_reason 포함) |
| POST | `/api/survey/recommend` | 설문 → 맛 벡터 → 추천 원스텝 |
| POST | `/api/food/recommend` | 음식 이름 기반 추천 |

### 설문 · 취향
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/survey/convert` | 25문항 설문 → 맛 벡터 변환 |
| POST | `/api/survey/bti-type` | 맛 벡터 → 술BTI 유형 판정 |
| POST | `/api/taste/update` | 취향 업데이트 (별점 or 축별 ratings dict) |
| GET | `/api/taste/history/{user_id}` | 취향 히스토리 + 진화된 맛 벡터 조회 |

### 채팅
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/chat` | 전통주 전문 AI 채팅 + 후속 질문 추천 |

### 레시피 AI
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/recipe/suggest-sub-ingredients` | 지역 특산 서브재료 추천 |
| POST | `/api/recipe/suggest-flavor-tags` | 맛 태그 자동 생성 |
| POST | `/api/recipe/suggest-summary` | 프로젝트 요약문 자동 생성 |

### 법률 필터링
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/law/filter` | 레시피/펀딩 법률 위반 검토 |
| GET | `/api/law/info` | 전통주 관련 주요 법령 목록 |

### 인사이트
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/insight` | 집계 + 예측 + 군집화 + AI 리포트 |

### RAG 검색
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/rag/search` | 전통주 전문 문서 검색 |
| GET | `/api/rag/category/{category}` | 카테고리별 문서 조회 |

### 크롤러
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/crawler/check` | 신규 전통주 감지 + 맛 벡터 자동 생성 |

### 전통주 등록 요청
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/drinks/request` | 사용자 전통주 등록 요청 접수 |
| GET | `/api/drinks/requests` | 등록 요청 목록 조회 (관리자) |
| POST | `/api/drinks/requests/{id}/approve` | 요청 승인 + 맛 벡터 자동 생성 |

## 환경변수

```env
GEMINI_API_KEY=발급받은키
LAW_API_KEY=국가법령정보센터키
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/juddam
REDIS_URL=redis://localhost:6379
```

## Gemini API 에러 처리

| 상황 | HTTP 상태 | 응답 메시지 |
|------|-----------|-------------|
| 429 / quota exceeded | 503 | 현재 AI 서비스가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요. |
| 연결 오류 | 500 | AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요. |

## 테스트

```bash
pytest tests/ -v
```

## 주의사항

- `.env` 파일은 절대 커밋하지 마세요
- 외부 API 호출은 Mock 테스트 먼저 진행하세요
- Gemini API 무료 티어는 분당 호출 한도가 있습니다 (한도 초과 시 503 반환)

## 백엔드 연동

### 연동 방식
- **공유 DB 방식**: 백엔드와 AI 서버가 동일한 PostgreSQL DB 공유
- **API 통신**: 백엔드가 AI 서버 API 직접 호출

### 주요 DB 테이블
- `users` — 사용자 정보
- `drinks` — 전통주 정보 (맛 벡터 포함)
- `user_taste_history` — 취향 히스토리
- `recommendations` — 추천 기록

## AWS 배포

AWS EC2 배포 방법은 [DEPLOYMENT.md](DEPLOYMENT.md)를 참고하세요.

| 구성 | 사양 |
|------|------|
| EC2 | Ubuntu 22.04 LTS, t3.medium 이상 |
| RDS | PostgreSQL 15.x |
| Nginx | 리버스 프록시 |

## 문서

- [API_GUIDE.md](API_GUIDE.md) — API 상세 가이드 (전체 엔드포인트 예시 포함)
- [DEPLOYMENT.md](DEPLOYMENT.md) — AWS 배포 가이드
- [SKILL.md](SKILL.md) — AI 서버 설계 원칙
- [CLAUDE.md](CLAUDE.md) — Claude Code 설정
