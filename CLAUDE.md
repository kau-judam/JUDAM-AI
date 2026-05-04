# 주담 AI 서버 — Claude Code 설정

## 이 프로젝트에 대해
소비자 맞춤형 전통주 공동 기획 펀딩 플랫폼 "주담"의 AI 서버.
담당자: 황주원 (AI 파트)

## 핵심 파일 위치
- SKILL.md: AI 서버 설계 원칙 및 개념 정리
- PROMPTS.md: 단계별 개발 프롬프트 모음
- app/main.py: FastAPI 서버 진입점
- .env: API 키 (절대 커밋 금지)

## 개발 순서
1. 8주차: CSV 파싱 → Gemini 라벨링 → 자체 모델 학습
2. 8~9주차: 코사인 유사도 추천 API
3. 9주차: 술BTI 문항 확정 → 벡터 변환 로직
4. 10주차: 법률 필터링 + 인사이트 대시보드
5. 11주차~: 임베딩 고도화 + 하이브리드 추천

## Claude Code 사용 규칙
1. 새 작업 시작 전 항상 SKILL.md 먼저 읽기
2. 코드 작성 전 설계 의도 확인
3. 외부 API 호출하는 코드는 Mock 테스트 먼저
4. .env 파일은 절대 출력하거나 커밋하지 말 것
5. 에러 발생 시 전체 스택 트레이스 보여주기

## 환경변수 (.env)
```
GEMINI_API_KEY=발급받은키
LAW_API_KEY=국가법령정보센터키
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/juddam
REDIS_URL=redis://localhost:6379
```

## 자주 쓰는 명령어
```bash
# 서버 실행
uvicorn app.main:app --reload --port 8000

# 테스트 실행
pytest tests/ -v

# CSV 파이프라인 실행
python app/data_pipeline.py

# 모델 학습
python app/model_trainer.py
```
