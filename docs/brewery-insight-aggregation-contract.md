# 양조장 인사이트 집계 계약 초안

## 원칙

- 백엔드가 서비스 DB의 게시물, 댓글, 성공 펀딩, BTI 관심 데이터를 비식별 집계해 AI 서버에 전달한다.
- AI 서버는 백엔드 DB 테이블명이나 관계를 추측해 직접 JOIN하지 않는다.
- 개인 식별정보, 원문 작성자 ID, 이메일, 전화번호, 주소는 전달하지 않는다.
- 실제 데이터가 없으면 빈 배열과 `data_source: "unavailable"`을 전달한다. 샘플 데이터를 실데이터처럼 표시하지 않는다.

## 요청 초안

향후 엔드포인트 후보: `POST /api/insight/brewery-analysis`

```json
{
  "period": {
    "from": "2026-05-01",
    "to": "2026-05-31",
    "timezone": "Asia/Seoul"
  },
  "data_source": "backend_aggregation",
  "posts": [
    {
      "post_id": "post_001",
      "title": "청주 사과 막걸리 아이디어",
      "content_keywords": ["사과", "상큼한", "저도수"],
      "ingredients": ["사과", "쌀"],
      "flavor_tags": ["상큼한", "청량한"],
      "view_count": 120,
      "interest_count": 32,
      "comment_count": 8,
      "created_at": "2026-05-10T09:00:00+09:00"
    }
  ],
  "comments": [
    {
      "post_id": "post_001",
      "content_keywords": ["낮은 도수", "사과향"],
      "created_at": "2026-05-11T10:00:00+09:00"
    }
  ],
  "successful_fundings": [
    {
      "ingredients": ["사과", "쌀"],
      "flavor_tags": ["상큼한", "청량한"],
      "region": "청주시",
      "achievement_rate": 142.5
    }
  ],
  "bti_interest_aggregates": [
    {
      "bti_code": "SLFUL",
      "interest_keywords": ["저도수", "과일향"],
      "count": 58
    }
  ]
}
```

## 최소 입력 필드

| 집계 | 필수 필드 |
|---|---|
| 게시물 | 제목, 내용 키워드, 재료, 맛 태그, 조회·관심·댓글 수, 작성일 |
| 댓글 | 텍스트 키워드, 게시물 ID, 작성일 |
| 성공 펀딩 | 재료, 맛 태그, 지역, 달성률 |
| BTI 관심 | `bti_code`, 관심 키워드, 건수 |

원문 전체 대신 분석에 필요한 키워드 배열을 권장한다. 댓글과 BTI 집계에는 사용자 식별자를 포함하지 않는다.

## 응답 초안

```json
{
  "data_source": "backend_aggregation",
  "analysis_period": {
    "from": "2026-05-01",
    "to": "2026-05-31"
  },
  "sample_counts": {
    "posts": 1,
    "comments": 1,
    "successful_fundings": 1,
    "bti_interest_aggregates": 1
  },
  "rising_keywords": ["사과", "저도수"],
  "popular_ingredients": ["사과", "쌀"],
  "popular_flavors": ["상큼한", "청량한"],
  "successful_funding_patterns": ["과일 재료와 저도수 조합"],
  "bti_group_interests": [
    {
      "bti_code": "SLFUL",
      "keywords": ["저도수", "과일향"],
      "count": 58
    }
  ],
  "product_planning_suggestions": ["청주 사과를 활용한 저도수·청량 콘셉트를 검토하세요."],
  "warnings": []
}
```

## 데이터 출처

| 값 | 의미 |
|---|---|
| `backend_aggregation` | 백엔드가 실제 서비스 데이터를 집계해 전달 |
| `unavailable` | 분석 가능한 실제 데이터 없음 |

`sample`, `demo`, 메모리 fallback 데이터를 실제 양조장 인사이트 응답으로 사용하지 않는다.

## 미확정 사항

- 백엔드의 실제 집계 엔드포인트와 인증 방식
- 게시물 관심 수의 정의
- 성공 펀딩 판정 기준
- 분석 주기와 최소 표본 수
- 키워드 추출을 백엔드와 AI 서버 중 어디서 담당할지

위 항목이 확정되기 전에는 AI 서버가 서비스 DB 테이블을 직접 조회하거나 JOIN하지 않는다.
