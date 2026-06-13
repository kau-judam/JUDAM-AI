"""통합 전통주 챗봇 계약 테스트."""

from collections import defaultdict
from types import SimpleNamespace

import pytest

from app import chat as chat_module


DRINKS = [
    {
        "id": "d1",
        "name": "테스트 생막걸리",
        "brewery": "테스트양조",
        "abv": 6.0,
        "region": "청주시",
        "features": "파전과 잘 어울린다.",
        "ingredients": "쌀",
        "taste_vector": {"sweetness": 5.0},
    },
    {
        "id": "d2",
        "name": "테스트 저도주",
        "brewery": "견본양조",
        "abv": 3.0,
        "region": "서울",
        "features": "가벼운 안주와 잘 어울린다.",
        "ingredients": "쌀",
        "taste_vector": {"sweetness": 3.0},
    },
    {
        "id": "d3",
        "name": "테스트 약주",
        "brewery": "샘플양조",
        "abv": 12.0,
        "region": "경기",
        "features": "육류 안주와 잘 어울린다.",
        "ingredients": "쌀",
        "taste_vector": {"sweetness": 2.0},
    },
]


class FakeRecommender:
    def __init__(self):
        self.drinks = DRINKS
        self.funding_drinks = []
        self.approved_drinks = []
        self.user_taste_history = defaultdict(list)

    def get_evolved_taste_vector(self, _user_id):
        return {"sweetness": 5.0}

    def recommend(self, **_kwargs):
        return [DRINKS[0], DRINKS[2], DRINKS[1]]


def _request(recommender, profiles=None):
    app = SimpleNamespace(
        state=SimpleNamespace(recommender=recommender, user_profiles=profiles or {})
    )
    return SimpleNamespace(app=app)


@pytest.fixture(autouse=True)
def stable_next_actions(monkeypatch):
    async def fake_actions(_question, _answer, drinks):
        return [f"{drinks[0]['name']}의 안주는?" if drinks else "전통주 추천은?", "도수를 비교해 주세요."]

    monkeypatch.setattr(chat_module, "_generate_next_actions", fake_actions)


@pytest.mark.asyncio
async def test_general_recommendation_uses_only_catalog_products():
    response = await chat_module.chat(
        chat_module.ChatRequest(message="전통주 추천해줘"),
        _request(FakeRecommender()),
    )
    assert response.personalization_source == "general"
    assert "일반 추천" in response.response
    assert {item["name"] for item in response.referenced_drinks} <= {drink["name"] for drink in DRINKS}
    assert "없는브랜드" not in response.response


@pytest.mark.asyncio
async def test_taste_history_personalization():
    recommender = FakeRecommender()
    recommender.user_taste_history["u1"].append({"rating": 5})
    response = await chat_module.chat(
        chat_module.ChatRequest(message="막걸리 추천해줘", user_id="u1"),
        _request(recommender),
    )
    assert response.personalization_source == "taste_history"
    assert "취향 정보를 반영" in response.response


@pytest.mark.asyncio
async def test_survey_profile_personalization():
    response = await chat_module.chat(
        chat_module.ChatRequest(message="막걸리 추천해줘", user_id="u2"),
        _request(FakeRecommender(), {"u2": {"taste_vector": {"sweetness": 8.0}}}),
    )
    assert response.personalization_source == "survey_profile"


@pytest.mark.asyncio
async def test_follow_up_pairing_and_lowest_abv():
    history = [{
        "role": "assistant",
        "content": "테스트 생막걸리와 테스트 저도주를 추천합니다.",
        "referenced_drinks": [{"name": "테스트 생막걸리"}, {"name": "테스트 저도주"}],
    }]
    pairing = await chat_module.chat(
        chat_module.ChatRequest(message="첫 번째 술에 어울리는 안주는?", history=history),
        _request(FakeRecommender()),
    )
    lowest = await chat_module.chat(
        chat_module.ChatRequest(message="그중 낮은 도수는?", history=history),
        _request(FakeRecommender()),
    )
    assert pairing.intent == "food_pairing"
    assert pairing.referenced_drinks[0]["name"] == "테스트 생막걸리"
    assert lowest.intent == "lowest_abv"
    assert lowest.referenced_drinks[0]["name"] == "테스트 저도주"


@pytest.mark.asyncio
async def test_product_comparison_and_relevant_next_actions():
    history = [{
        "role": "assistant",
        "content": "테스트 생막걸리와 테스트 약주",
        "referenced_drinks": [{"name": "테스트 생막걸리"}, {"name": "테스트 약주"}],
    }]
    response = await chat_module.chat(
        chat_module.ChatRequest(message="두 제품 비교해줘", history=history),
        _request(FakeRecommender()),
    )
    assert response.intent == "compare_drinks"
    assert len(response.referenced_drinks) == 2
    assert response.next_actions == response.suggested_questions
    assert any("테스트 생막걸리" in question for question in response.next_actions)


@pytest.mark.asyncio
async def test_direct_product_explanation_uses_named_catalog_product():
    response = await chat_module.chat(
        chat_module.ChatRequest(message="테스트 약주 특징 알려줘"),
        _request(FakeRecommender()),
    )
    assert response.intent == "drink_explanation"
    assert response.referenced_drinks[0]["name"] == "테스트 약주"
