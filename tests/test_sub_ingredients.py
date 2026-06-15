"""서브재료 지역 요청 계약 테스트."""

import pytest

from app.models import SubIngredientsRequest
from app.recipe import RecipeAI


def test_snake_case_contract_and_legacy_alias():
    official = SubIngredientsRequest(main_ingredient="사과", region="청주시")
    legacy = SubIngredientsRequest(mainIngredient="사과", region="청주시")
    assert official.main_ingredient == legacy.main_ingredient == "사과"


@pytest.mark.asyncio
async def test_apple_cheongju_uses_real_nongsaro_candidates():
    result = await RecipeAI().suggest_sub_ingredients("사과", "청주시")
    assert result["data_source"] == "nongsaro_api"
    assert result["sub_ingredients"]
    assert result["traditional_liquor_status"] == "NEEDS_REVIEW"


@pytest.mark.asyncio
async def test_missing_region_and_unknown_ingredient_do_not_raise():
    missing = await RecipeAI().suggest_sub_ingredients("사과", None)
    unknown = await RecipeAI().suggest_sub_ingredients("존재하지않는재료", "존재하지않는지역")
    assert missing["data_source"] == "unavailable"
    assert unknown["data_source"] == "unavailable"
    assert missing["sub_ingredients"] == unknown["sub_ingredients"] == []


@pytest.mark.asyncio
async def test_manual_fallback(monkeypatch):
    monkeypatch.setattr("app.recipe._load_local_products", lambda: [])
    result = await RecipeAI().suggest_sub_ingredients("감귤", "제주도")
    assert result["data_source"] == "manual"
    assert all(item in {"제주 감귤", "한라봉"} for item in result["sub_ingredients"])


@pytest.mark.asyncio
async def test_gemini_selects_only_from_real_candidates(monkeypatch):
    recipe_ai = RecipeAI()
    recipe_ai.gemini_api_key = "test-key"

    async def fake_select(_main_ingredient, candidates):
        return [candidates[-1], candidates[0]]

    monkeypatch.setattr(recipe_ai, "_gemini_select_sub_ingredients", fake_select)
    result = await recipe_ai.suggest_sub_ingredients("사과", "청주시")

    assert result["data_source"] == "nongsaro_api"
    assert len(result["sub_ingredients"]) == 2


@pytest.mark.asyncio
async def test_gemini_selection_failure_falls_back_to_real_candidates(monkeypatch):
    recipe_ai = RecipeAI()
    recipe_ai.gemini_api_key = "test-key"

    async def fail_select(*_args, **_kwargs):
        raise RuntimeError("provider failure")

    monkeypatch.setattr(recipe_ai, "_gemini_select_sub_ingredients", fail_select)
    result = await recipe_ai.suggest_sub_ingredients("사과", "청주시")

    assert result["data_source"] == "nongsaro_api"
    assert result["sub_ingredients"]
