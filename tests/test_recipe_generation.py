"""레시피 생성 기능 요청 계약 테스트."""

from app.image_generator import _as_png_base64, build_image_prompt
from app.models import FlavorTagsRequest, SummaryRequest


def test_flavor_summary_and_image_contracts():
    flavor = FlavorTagsRequest(
        title="청주 사과 프로젝트",
        main_ingredient="사과",
        sub_ingredients=["청주 쌀"],
        abv_range="6~8도",
    )
    summary = SummaryRequest(
        title=flavor.title,
        main_ingredient=flavor.main_ingredient,
        sub_ingredients=flavor.sub_ingredients,
        abv_range=flavor.abv_range,
        flavor_tags=["상큼한"],
        concept="청주의 가을",
    )
    prompt = build_image_prompt(
        summary.title,
        "사과 특산주 프로젝트",
        summary.flavor_tags,
        "청주시",
        summary.main_ingredient,
        summary.sub_ingredients,
        summary.concept,
        {"sweetness": 7, "body": 4},
        42,
    )
    assert all(value in prompt for value in ("사과", "청주 쌀", "청주시", "청주의 가을"))


def test_image_result_is_normalized_to_png():
    tiny_png = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII="
    )
    normalized = _as_png_base64(tiny_png)
    assert normalized
