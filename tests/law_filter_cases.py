# -*- coding: utf-8 -*-
"""
법률 필터 테스트셋 (라벨링된 케이스)

카테고리:
  A. 명백한 위반    → 차단 기대 (block)
  B. 애매한 위반    → 차단 기대 (block)  ★핵심: 함의/암시 표현, 리터럴 키워드 없음
  C. 정상 함정      → 통과 기대 (pass)   ★핵심: 위반 키워드를 건드리지만 실제론 정상
  D. 완전 정상      → 통과 기대 (pass)

각 케이스: id, category(A/B/C/D), title, description, ingredients,
           content_type("recipe"|"funding"), expected("block"|"pass")

이 파일은 데이터만 정의한다 (실행 로직 없음). 러너: tests/run_law_filter_test.py
"""

CASES = [
    # ─────────────────────────────────────────────────────────────
    # A. 명백한 위반 (block 기대)
    # ─────────────────────────────────────────────────────────────
    {
        "id": "A1", "category": "A", "expected": "block", "content_type": "recipe",
        "title": "숙취 없는 막걸리",
        "description": "아무리 마셔도 숙취가 없는 막걸리입니다",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "A2", "category": "A", "expected": "block", "content_type": "recipe",
        "title": "청소년도 마시는 전통주",
        "description": "청소년도 부담 없이 즐기는 순한 전통주",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "A3", "category": "A", "expected": "block", "content_type": "recipe",
        "title": "암 예방 전통주",
        "description": "꾸준히 마시면 암 예방에 효과적인 약주",
        "ingredients": "쌀, 누룩, 약재, 물",
    },
    {
        "id": "A4", "category": "A", "expected": "block", "content_type": "funding",
        "title": "원금 보장 막걸리 펀딩",
        "description": "투자하면 원금 보장에 100% 수익 확정",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "A5", "category": "A", "expected": "block", "content_type": "recipe",
        "title": "무조건 최고의 명주",
        "description": "대한민국에서 무조건 최고, 완벽한 명주입니다",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "A6", "category": "A", "expected": "block", "content_type": "recipe",
        "title": "다이어트 막걸리",
        "description": "마시면 살이 빠지는 다이어트 전용 막걸리",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "A7", "category": "A", "expected": "block", "content_type": "recipe",
        "title": "간 건강 지키는 막걸리",
        "description": "간 건강을 지켜주고 해독에 좋은 막걸리",
        "ingredients": "쌀, 누룩, 헛개나무, 물",
    },

    # ─────────────────────────────────────────────────────────────
    # B. 애매한 위반 (block 기대) — 함의/암시, 리터럴 위반 키워드 회피
    # ─────────────────────────────────────────────────────────────
    {
        "id": "B1", "category": "B", "expected": "block", "content_type": "recipe",
        "title": "다음날 개운한 막걸리",
        "description": "전날 마셔도 다음날 아침이 개운한 막걸리",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "B2", "category": "B", "expected": "block", "content_type": "recipe",
        "title": "면역력 챙기는 전통주",
        "description": "한 잔으로 면역력을 챙기는 약주",
        "ingredients": "쌀, 누룩, 약재, 물",
    },
    {
        "id": "B3", "category": "B", "expected": "block", "content_type": "recipe",
        "title": "취하지 않는 순한 술",
        "description": "아무리 마셔도 잘 취하지 않는 신기한 술",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "B4", "category": "B", "expected": "block", "content_type": "recipe",
        "title": "피로 회복 막걸리",
        "description": "하루의 피로 회복에 도움을 주는 막걸리",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "B5", "category": "B", "expected": "block", "content_type": "funding",
        "title": "고수익률 막걸리 펀딩",
        "description": "안정적으로 높은 수익률을 돌려드리는 무위험 투자",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "B6", "category": "B", "expected": "block", "content_type": "recipe",
        "title": "몸을 정화하는 디톡스 막걸리",
        "description": "체내 노폐물을 빼주는 디톡스 막걸리",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "B7", "category": "B", "expected": "block", "content_type": "recipe",
        "title": "수험생 집중 막걸리",
        "description": "공부하는 수험생도 한 잔씩 즐기는 막걸리",
        "ingredients": "쌀, 누룩, 물",
    },

    # ─────────────────────────────────────────────────────────────
    # C. 정상 함정 (pass 기대) — 위반 키워드를 건드리지만 합법
    # ─────────────────────────────────────────────────────────────
    {
        "id": "C1", "category": "C", "expected": "pass", "content_type": "recipe",
        "title": "깔끔한 목넘김 막걸리",
        "description": "끝맛이 깔끔한 목넘김이 일품인 막걸리",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "C2", "category": "C", "expected": "pass", "content_type": "recipe",
        "title": "전통 방식 그대로 빚은 약주",
        "description": "옛 전통 방식 그대로 정성껏 빚은 약주",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "C3", "category": "C", "expected": "pass", "content_type": "recipe",
        "title": "완벽한 균형의 청주",
        "description": "단맛과 산미가 완벽한 균형을 이루는 청주",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "C4", "category": "C", "expected": "pass", "content_type": "recipe",
        "title": "프리미엄 원료 막걸리",
        "description": "엄선한 프리미엄 원료로 만든 막걸리",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "C5", "category": "C", "expected": "pass", "content_type": "recipe",
        "title": "선물용으로 좋은 고급 약주",
        "description": "명절 선물용으로 좋은 고급 약주 세트",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "C6", "category": "C", "expected": "pass", "content_type": "funding",
        "title": "정직한 약주 펀딩",
        "description": "투자 수익은 보장하지 않으며 원금 손실 위험이 있습니다",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "C7", "category": "C", "expected": "pass", "content_type": "recipe",
        "title": "약주 본연의 깊은 맛",
        "description": "약주 본연의 깊고 묵직한 풍미를 살린 술",
        "ingredients": "쌀, 누룩, 물",
    },

    # ─────────────────────────────────────────────────────────────
    # D. 완전 정상 (pass 기대)
    # ─────────────────────────────────────────────────────────────
    {
        "id": "D1", "category": "D", "expected": "pass", "content_type": "recipe",
        "title": "달콤한 복숭아 향 막걸리",
        "description": "복숭아 향이 달콤하게 퍼지는 막걸리",
        "ingredients": "쌀, 누룩, 복숭아, 물",
    },
    {
        "id": "D2", "category": "D", "expected": "pass", "content_type": "recipe",
        "title": "쌀과 누룩의 구수한 막걸리",
        "description": "쌀과 누룩의 구수한 풍미가 살아있는 막걸리",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "D3", "category": "D", "expected": "pass", "content_type": "recipe",
        "title": "제주 감귤 막걸리",
        "description": "제주산 감귤로 빚은 상큼한 막걸리",
        "ingredients": "쌀, 감귤, 누룩, 물",
    },
    {
        "id": "D4", "category": "D", "expected": "pass", "content_type": "recipe",
        "title": "경기미로 빚은 청주",
        "description": "경기도 쌀 100%로 빚은 맑은 청주",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "D5", "category": "D", "expected": "pass", "content_type": "recipe",
        "title": "탄산이 톡 쏘는 막걸리",
        "description": "청량한 탄산감이 톡 쏘는 막걸리",
        "ingredients": "쌀, 누룩, 물",
    },
    {
        "id": "D6", "category": "D", "expected": "pass", "content_type": "recipe",
        "title": "고소한 땅콩 막걸리",
        "description": "고소한 땅콩 풍미가 매력적인 막걸리",
        "ingredients": "쌀, 누룩, 땅콩, 물",
    },
    {
        "id": "D7", "category": "D", "expected": "pass", "content_type": "funding",
        "title": "국화 향 청주 공동구매",
        "description": "국화 향이 은은한 청주를 함께 만드는 프로젝트",
        "ingredients": "쌀, 누룩, 국화, 물",
    },
]
