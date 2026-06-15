"""추천 유사도 정규화 회귀 테스트."""

import pytest

from app.core.recommender import AdvancedMakgeolliRecommender


AXES = [
    'sweetness', 'body', 'carbonation', 'flavor',
    'alcohol', 'acidity', 'aroma_intensity', 'finish',
]


def _vector(*values):
    return dict(zip(AXES, values))


def _drink(drink_id, vector, *, features='', is_funding=False):
    return {
        'id': drink_id,
        'name': drink_id,
        'abv': 6.0,
        'brewery': f'brewery-{drink_id}',
        'region': '',
        'features': features,
        'ingredients': '',
        'taste_vector': vector,
        'is_funding': is_funding,
    }


@pytest.fixture
def recommender(tmp_path):
    instance = AdvancedMakgeolliRecommender(data_file=tmp_path / 'missing.json')
    instance.drinks = []
    return instance


def test_no_food_uses_normalized_taste_only(recommender):
    user = _vector(5, 5, 5, 5, 5, 5, 5, 5)
    drink = _drink('base', _vector(5, 5, 5, 5, 5, 5, 5, 4))

    similarity = recommender.multi_source_similarity(user, drink)

    assert similarity == pytest.approx(recommender.cosine_similarity(user, drink['taste_vector']))


def test_food_pairing_does_not_change_recommendation_similarity(recommender):
    user = _vector(5, 5, 5, 5, 5, 5, 5, 5)
    drink = _drink('paired', _vector(5, 5, 5, 5, 5, 5, 5, 4), features='고기와 잘 어울림')
    taste = recommender.cosine_similarity(user, drink['taste_vector'])

    similarity = recommender.multi_source_similarity(user, drink, user_food_pairings=['고기'])

    assert similarity == pytest.approx(taste)


def test_all_weights_are_ignored_and_score_is_clamped(recommender):
    user = _vector(1, 1, 1, 1, 1, 1, 1, 1)
    opposite = _drink('opposite', _vector(-1, -1, -1, -1, -1, -1, -1, -1))
    old_weights = {'taste': 0.65, 'ingredient': 0.15, 'region': 0.1, 'food': 0.1}

    assert recommender.multi_source_similarity(user, opposite, old_weights) == 0.0


def test_funding_injection_uses_same_similarity_formula(recommender):
    user = _vector(5, 5, 5, 5, 5, 5, 5, 5)
    base = _drink('base', user)
    funding = _drink(
        'funding',
        _vector(5, 5, 5, 5, 5, 5, 5, 4),
        features='고기와 잘 어울림',
        is_funding=True,
    )
    recommender.drinks = [base]
    recommender.funding_drinks = [funding]

    recommendations = recommender.recommend(user, top_k=1, user_food_pairings=['고기'])
    injected = recommendations[0]
    expected = recommender.multi_source_similarity(user, funding, user_food_pairings=['고기'])

    assert injected['id'] == 'funding'
    assert injected['similarity'] == pytest.approx(expected)
    assert injected['similarity_percent'] == round(expected * 100, 1)
    assert injected['match_reason']
