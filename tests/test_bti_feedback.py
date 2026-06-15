"""BTI 피드백 선택 필드 수집 계약 테스트."""

import pytest

from app import main
from app.models import BTIFeedbackRequest


def test_bti_feedback_optional_collection_fields():
    request = BTIFeedbackRequest(
        user_id="user_001",
        bti_code="SHFC",
        is_correct=False,
        wrong_axes=["sweetness", "body"],
        feedback_reason="단맛과 바디감이 실제 취향과 달라요.",
    )

    assert request.wrong_axes == ["sweetness", "body"]
    assert request.feedback_reason == "단맛과 바디감이 실제 취향과 달라요."
    assert request.actual_preference is None


@pytest.mark.asyncio
async def test_bti_feedback_entry_collects_optional_fields(monkeypatch):
    captured = {}

    async def fake_insert(entry):
        captured.update(entry)
        return True

    async def fake_count():
        return 1

    monkeypatch.setattr(main.db, "insert_bti_feedback", fake_insert)
    monkeypatch.setattr(main.db, "get_bti_feedback_count", fake_count)

    response = await main.bti_feedback(
        BTIFeedbackRequest(
            user_id="user_001",
            bti_code="SHFC",
            is_correct=False,
            wrong_axes=["sweetness", "carbonation"],
            feedback_reason="조금 더 드라이한 취향입니다.",
        )
    )

    assert captured["wrong_axes"] == ["sweetness", "carbonation"]
    assert captured["feedback_reason"] == "조금 더 드라이한 취향입니다."
    assert captured["original_code"] == "SHFC"
    assert response["storage"] == "db"
