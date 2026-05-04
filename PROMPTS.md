# 주담 AI 서버 — Claude Code 프롬프트 모음
# 중간 발표 피드백 반영 고도화 버전

## 사용법
juddam-ai/ 폴더에서 claude 실행 후 아래 프롬프트 붙여넣기.
항상 SKILL.md 먼저 읽도록 프롬프트 시작.

---

## 0단계 — 앙커 데이터 구축 (라벨링 신뢰도 확보, 지금 바로)

### 0-1. 앙커 데이터 파일 생성
```
SKILL.md를 읽고 시작해줘.

data/anchors.json 파일을 만들어줘.
이건 Gemini 라벨링의 기준점이 되는 앙커 데이터야.
실제 시음 후 직접 점수를 매긴 전통주 10~20개가 들어가는 파일이야.

형식:
{
  "anchors": [
    {
      "name": "전통주명",
      "manufacturer": "제조사",
      "category": "막걸리/청주/약주/소주/과실주",
      "abv": 도수(float),
      "sweetness": 0~10,
      "body": 0~10,
      "carbonation": 0~10,
      "flavor": 0~10,
      "alcohol": 0~10,
      "note": "특징 메모",
      "source": "직접시음/전문가리뷰/크라우드소싱"
    }
  ],
  "scoring_guide": {
    "sweetness": "0=전혀 달지 않음(소주), 5=보통(일반 막걸리), 10=매우 달콤(과실주)",
    "body": "0=물처럼 가벼움, 5=보통, 10=매우 묵직하고 걸쭉함",
    "carbonation": "0=탄산 없음, 5=약한 탄산, 10=강한 탄산",
    "flavor": "0=전통적 누룩향, 5=보통, 10=독특한 과일/허브향",
    "alcohol": "0=무알코올, 5=10% 내외, 10=25% 이상"
  }
}

대표적인 전통주 10개로 초기 데이터 채워줘.
(장수막걸리, 복순도가, 안동소주, 문배술, 이강주 등 유명한 것들로)
```

### 0-2. 앙커 기반 Gemini 라벨링 프롬프트 생성기
```
SKILL.md를 읽고 시작해줘.

app/gemini_labeler.py 파일을 만들어줘.
앙커 데이터를 활용해서 일관성 있는 맛 라벨링을 하는 모듈이야.

핵심 차이점:
기존 방식: "이 술의 맛을 평가해줘"
개선 방식: 앙커 10개를 예시로 같이 넘겨서 "이 기준에 맞춰서 평가해줘"

요구사항:
1. data/anchors.json에서 앙커 데이터 로드
2. 앙커를 포함한 프롬프트 생성 함수: build_labeling_prompt(drink_info) → str
3. Gemini API 호출 및 JSON 파싱
4. 신뢰도 점수 계산:
   - 비슷한 앙커 3개 찾기 (재료/유형 기반)
   - Gemini 결과와 앙커 평균의 차이로 신뢰도 계산
   - 신뢰도 0.7 미만이면 재시도
5. 배치 처리: 10개씩, Rate limit 시 5초 대기
6. 결과: data/processed/drinks_labeled.csv + 신뢰도 컬럼 포함

타입 힌트, 에러 처리, logging 필수.
```

---

## 1단계 — 전통주 RAG DB 구축 (도메인 전문성 확보)

### 1-1. RAG 문서 수집 및 벡터화
```
SKILL.md를 읽고 시작해줘.

app/rag.py 파일을 만들어줘.
전통주 전문 지식 RAG DB를 구축하고 검색하는 모듈이야.

문서 소스 (텍스트 파일로 준비할 예정):
- rag_db/traditional_spirits.txt: 전통주 종류별 특성
- rag_db/fermentation.txt: 발효 방법 및 원리
- rag_db/ingredients.txt: 주요 원재료와 맛 특성

요구사항:
1. 문서 로드 및 청크 분할 (500자씩, 100자 겹침)
2. TF-IDF로 벡터화 및 저장
3. 검색 함수: search_knowledge(query, top_k=3) → list[str]
4. 관련 문서 검색 후 Gemini 프롬프트에 포함시키는 helper 함수
5. 캐시: 동일 쿼리는 파일 캐시로 처리

문서 파일이 없으면 기본 전통주 지식 10개를 직접 생성해서 초기화.
타입 힌트, 에러 처리 필수.
```

---

## 2단계 — 고도화된 추천 API

### 2-1. 컨텍스트 기반 추천
```
SKILL.md를 읽고 시작해줘.

app/recommend.py 파일을 만들어줘.
컨텍스트를 반영한 고도화된 전통주 추천 API야.

요구사항:
1. POST /api/recommend 엔드포인트
2. 요청 바디 (Pydantic):
   {
     "user_vector": {sweetness, body, carbonation, flavor, alcohol},
     "context": {
       "season": "spring|summer|autumn|winter|null",
       "occasion": "daily|meal|celebration|outdoor|null",
       "mood": "refreshing|relaxing|special|null"
     },
     "top_k": int = 10,
     "exclude_ids": list[int] = []
   }
3. 컨텍스트 가중치 적용:
   - summer + refreshing → carbonation 가중치 1.5배
   - meal → body 가중치 1.3배
   - celebration → alcohol 가중치 허용 범위 확대
4. 코사인 유사도 계산 (컨텍스트 가중치 적용된 벡터로)
5. 다양성 보장: 같은 제조사 술은 최대 2개만 포함
6. Redis 캐싱 (TTL 30분)
7. 응답: 술 정보 + 유사도 점수 + 추천 이유 한 줄

타입 힌트, 에러 처리, logging 필수.
```

### 2-2. 취향 진화 트래킹
```
SKILL.md를 읽고 시작해줘.

app/taste_evolution.py 파일을 만들어줘.
사용자가 술을 기록할 때마다 맛 벡터를 업데이트하는 모듈이야.

요구사항:
1. POST /api/taste/update 엔드포인트
2. 요청: {user_id, drink_id, rating(1~5), tags: list[str]}
3. 벡터 업데이트 로직:
   - 초기: 술BTI 벡터 100%
   - 평가 1개: 술BTI 90% + 평가 10%
   - 평가 10개: 술BTI 50% + 평가 50%
   - 평가 50개 이상: 술BTI 20% + 평가 80%
   - 별점 5점: 해당 술 방향으로 이동
   - 별점 1점: 반대 방향으로 이동
4. GET /api/taste/history/{user_id}: 취향 변화 히스토리
5. 마이페이지 레이더 차트용 데이터 반환
6. DB에 벡터 변화 이력 저장 (시각화용)

타입 힌트, 에러 처리, logging 필수.
```

---

## 3단계 — 인사이트 대시보드 (예측 로직 구체화)

### 3-1. 트렌드 예측 모듈
```
SKILL.md를 읽고 시작해줘.

app/trend_predictor.py 파일을 만들어줘.
월별 취향 데이터로 다음 달 트렌드를 예측하는 모듈이야.

요구사항:
1. 함수: predict_next_month(monthly_values: list[float]) → dict
   - Holt-Winters 지수평활법 사용 (statsmodels)
   - 최소 3개월 데이터 필요, 부족하면 이동평균으로 대체
   - 반환: {predicted_value, trend_direction, change_rate, confidence}
2. 전체 5개 축 동시 예측
3. 변화율 계산: (예측값 - 현재값) / 현재값 * 100
4. 신뢰 구간 포함 (80% CI)
5. Gemini에게 예측 결과 전달 → 생산 권고 자연어 생성

statsmodels 라이브러리 사용. 타입 힌트, 에러 처리 필수.
```

### 3-2. 레시피 군집화 모듈
```
SKILL.md를 읽고 시작해줘.

app/recipe_clusterer.py 파일을 만들어줘.
사용자 레시피를 군집화해서 수요 패턴을 파악하는 모듈이야.

요구사항:
1. POST /api/recipes/cluster 엔드포인트
2. 레시피 텍스트들을 TF-IDF로 벡터화
3. K-Means로 군집화 (k=10, 자동 최적화 포함)
4. 각 군집의 키워드 상위 5개 추출
5. 군집 크기 순으로 정렬 (= 수요 규모)
6. 제품화 가능성 점수:
   - 군집 크기 (관심 레시피 수)
   - 펀딩 전환율
   - 재료 조달 가능성 (지역 특산물 여부)
   조합해서 0~100 점수
7. 양조장 대시보드에 TOP 5 군집 + 제품화 점수 반환

타입 힌트, 에러 처리 필수.
```

### 3-3. 통합 인사이트 API
```
SKILL.md를 읽고 시작해줘.

app/insight.py 파일을 만들어줘.
양조장 AI 인사이트 대시보드 통합 API야.

요구사항:
1. GET /api/insight/{brewery_id} 엔드포인트
2. 데이터 수집 (DB에서):
   - 이번 달 / 저번 달 사용자 맛 벡터 평균
   - 레시피 관심 수 상위 10개
   - 맛 투표 결과
3. 분석 3단계:
   A. 현재 집계 (Pandas): 각 축별 평균, 표준편차, 전월 대비 변화율
   B. 미래 예측 (trend_predictor): 다음 달 각 축 예측값
   C. 레시피 수요 (recipe_clusterer): TOP 3 수요 패턴
4. Gemini에게 A+B+C 전달 → 200자 이내 한국어 리포트 생성
5. 응답: {current_stats, predictions, recipe_demand, report, generated_at}
6. Redis 캐싱 (TTL 6시간)

타입 힌트, 에러 처리, logging 필수.
```

---

## 4단계 — 법률 필터링 (RAG + 국가법령정보센터 API)

### 4-1. 국가법령정보센터 API + RAG 결합
```
SKILL.md를 읽고 시작해줘.

app/filter.py 파일을 만들어줘.
국가법령정보센터 API + 전통주 RAG + Gemini를 결합한 법률 필터링 API야.

요구사항:
1. POST /api/filter 엔드포인트
2. 요청: {content_type, title, description, ingredients, target_region}
3. 법령 조회 (국가법령정보센터 API, .env의 LAW_API_KEY):
   - 주세법, 식품위생법, 전통주산업진흥법, 청소년보호법, 상표법
   - 24시간 파일 캐시
4. RAG 검색: 관련 전통주 규정 문서 검색
5. Gemini 프롬프트: 법령 조항 + RAG 결과 + 콘텐츠 모두 포함
6. 판단 항목:
   - 미성년자 타겟 여부
   - 금지 재료 포함 여부
   - 상표명 침해 가능성
   - 지역특산주 요건 (target_region과 원재료 매칭)
7. 위반 시 422 반환 + 구체적 수정 가이드

타입 힌트, 에러 처리, logging 필수.
```

---

## 디버깅 & 유틸 프롬프트

### 에러 발생 시
```
SKILL.md를 읽고 다음 에러를 수정해줘:
[에러 메시지]
수정 후 해당 함수 테스트 코드도 작성해줘.
```

### 성능 측정
```
SKILL.md를 읽고 다음 파일의 성능을 측정하는 코드를 작성해줘:
[파일명]
- 응답 시간 측정
- 추천 정확도: 앙커 데이터로 MAE 계산
- 처리량: 1초당 요청 수
결과를 로그로 출력해줘.
```

### 발표용 데모 데이터 생성
```
SKILL.md를 읽고 발표 데모용 테스트 데이터를 생성해줘.

1. 테스트 사용자 5명 맛 벡터 (다양한 취향으로)
2. 각 사용자별 추천 결과 예시
3. 인사이트 대시보드 샘플 데이터
4. 레시피 군집화 샘플 결과

data/demo/ 폴더에 JSON 파일로 저장.
발표할 때 바로 쓸 수 있는 형태로 만들어줘.
```

---

## 추가 — 테이스팅 노트 크롤링 (라벨링 신뢰도 핵심 해결책)

### 테이스팅 노트 크롤러 구현
```
SKILL.md를 읽고 시작해줘.

app/tasting_crawler.py 파일을 만들어줘.
전통주 테이스팅 노트를 크롤링해서 맛 벡터로 변환하는 모듈이야.

크롤링 대상:
1. 디시인사이드 전통주 마이너 갤러리
   URL: https://m.dcinside.com/board/ulisul
   추천수 높은 게시글만 (recommend=1 파라미터)
   
2. 홈술닷컴 상품 리뷰
   URL: https://www.homesool.com

요구사항:
1. requests + BeautifulSoup으로 크롤링
2. 술 이름 + 테이스팅 노트 텍스트 추출
3. 크롤링한 술 이름을 CSV 1,215개와 퍼지 매칭
   - python-Levenshtein or fuzz 라이브러리
   - 유사도 80% 이상만 매칭
4. 매칭된 술의 테이스팅 노트를 Gemini API로 구조화:
   프롬프트:
   "다음은 실제 소비자가 전통주를 마시고 남긴 테이스팅 노트입니다.
   이 내용을 기반으로 아래 5개 축을 0~10점으로 변환해주세요.
   JSON만 반환: {sweetness, body, carbonation, flavor, alcohol}
   
   sweetness: 0=드라이/쓴맛, 10=매우 달콤
   body: 0=물처럼 가벼움, 10=매우 묵직하고 걸쭉함
   carbonation: 0=탄산 없음, 10=강한 탄산
   flavor: 0=전통적 누룩/쌀 향, 10=독특한 과일/허브향
   alcohol: abv 기준으로 계산
   
   테이스팅 노트: {tasting_note}"
5. 결과를 data/tasting_notes_labeled.csv로 저장
   컬럼: drink_name, matched_drink_id, tasting_note_raw, sweetness, body, carbonation, flavor, alcohol, source_url, crawled_at
6. robots.txt 먼저 확인 후 허용된 경로만 크롤링
7. 요청 간 2초 딜레이 (서버 부하 방지)
8. 이미 크롤링한 URL은 스킵 (중복 방지)

설치: pip install requests beautifulsoup4 python-Levenshtein
타입 힌트, 에러 처리, logging 필수.
```

### 테이스팅 노트 기반 앙커 데이터 생성
```
SKILL.md를 읽고 시작해줘.

app/anchor_builder.py 파일을 만들어줘.
크롤링한 테이스팅 노트에서 고품질 앙커 데이터를 선별하는 모듈이야.

요구사항:
1. data/tasting_notes_labeled.csv 로드
2. 앙커 선별 기준:
   - 같은 술에 대한 리뷰가 3개 이상 있을 것
   - 리뷰들 간 맛 벡터 표준편차가 낮을 것 (= 일관된 평가)
   - 텍스트가 50자 이상 상세할 것
3. 선별된 앙커: 여러 리뷰의 맛 벡터 평균으로 최종 점수 계산
4. 상위 20개를 data/anchors.json으로 저장
5. 앙커 품질 리포트 출력:
   - 총 크롤링된 리뷰 수
   - 매칭된 전통주 수
   - 앙커로 선별된 수
   - 평균 리뷰 일관성 점수

타입 힌트, 에러 처리 필수.
```
