"""양조장 인증 OCR 업로드 계약 테스트."""

import base64

import pytest
from fastapi.testclient import TestClient

from app import main


VALID_BUSINESS_NUMBER = "214-88-12345"
COMPLETE_RAW_TEXT = (
    "사업자등록증\n사업자등록번호 214-88-12345\n상호 테스트양조장\n"
    "대표자 김테스트\n사업장 소재지 서울특별시 테스트구 견본로 1"
)
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII="
)
JPEG_BYTES = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "2wBDAf//////////////////////////////////////////////////////////////////////////////////////"
    "wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAF//8QAFBAB"
    "AAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/a"
    "AAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9oADAMBAAIA"
    "AwAAABAf/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPxB//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPxB//8QAFBABAAAAAAAA"
    "AAAAAAAAAAAAAP/aAAgBAQABPxB//9k="
)


def _image_bytes(image_format: str) -> bytes:
    """개인정보 없는 최소 가상 이미지를 반환한다."""
    return PNG_BYTES if image_format == "PNG" else JPEG_BYTES


def _pdf_bytes() -> bytes:
    """파일 시그니처 검증용 최소 가상 PDF를 생성한다."""
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"


def _ocr_result(**overrides):
    extracted = {
        "document_type": "사업자등록증",
        "is_valid_document": True,
        "brewery_name": "테스트양조장",
        "registration_number": VALID_BUSINESS_NUMBER,
        "business_number": VALID_BUSINESS_NUMBER,
        "owner_name": "김테스트",
        "address": "서울특별시 테스트구 견본로 1",
        "confidence": "high",
        "raw_text": COMPLETE_RAW_TEXT,
    }
    extracted.update(overrides)
    return {"status": "success", "extracted": extracted}


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("license.png", "image/png", _image_bytes("PNG")),
        ("license.jpg", "image/jpeg", _image_bytes("JPEG")),
        ("license.pdf", "application/pdf", _pdf_bytes()),
    ],
)
def test_supported_files_complete_but_never_auto_approve(
    monkeypatch, client, filename, content_type, content
):
    async def mock_extract(*_args, **_kwargs):
        return _ocr_result()

    monkeypatch.setattr(main._brewery_ocr, "extract_brewery_info", mock_extract)
    response = client.post(
        "/api/brewery/verify-ocr",
        files={"file": (filename, content, content_type)},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "COMPLETED"
    assert body["ocrSucceeded"] is True
    assert body["verified"] is False
    assert body["documentAssessment"] == "REVIEW_REQUIRED"
    assert body["summary"]["manualReviewOnly"] is True
    assert body["summary"]["businessNumber"] == VALID_BUSINESS_NUMBER


def test_business_license_temporary_compatibility(monkeypatch, client):
    async def mock_extract(*_args, **_kwargs):
        return _ocr_result()

    monkeypatch.setattr(main._brewery_ocr, "extract_brewery_info", mock_extract)
    response = client.post(
        "/api/brewery/verify-ocr",
        files={"businessLicense": ("license.png", _image_bytes("PNG"), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"


@pytest.mark.parametrize(
    ("name", "ocr_overrides", "warning_fragment"),
    [
        (
            "blurred",
            {"confidence": "low", "raw_text": "판독 불가"},
            "OCR 추출 신뢰도가 낮습니다.",
        ),
        (
            "missing",
            {"brewery_name": "", "owner_name": "", "address": ""},
            "필수 필드 누락: breweryName",
        ),
        (
            "unrelated",
            {
                "document_type": "인식불가",
                "is_valid_document": False,
                "brewery_name": "",
                "business_number": "",
                "registration_number": "",
                "owner_name": "",
                "address": "",
                "raw_text": "오늘의 일반 메모입니다. 인증 서류가 아닙니다.",
            },
            "지원 서류 종류로 확인되지 않았습니다.",
        ),
    ],
)
def test_review_warnings(monkeypatch, client, name, ocr_overrides, warning_fragment):
    async def mock_extract(*_args, **_kwargs):
        return _ocr_result(**ocr_overrides)

    monkeypatch.setattr(main._brewery_ocr, "extract_brewery_info", mock_extract)
    response = client.post(
        "/api/brewery/verify-ocr",
        files={"file": (f"{name}.png", _image_bytes("PNG"), "image/png")},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "COMPLETED"
    assert body["ocrSucceeded"] is True
    assert body["documentAssessment"] == "REVIEW_REQUIRED"
    assert warning_fragment in body["warnings"]


@pytest.mark.parametrize(
    ("files", "reason"),
    [
        (None, "NO_FILE"),
        ({"file": ("empty.png", b"", "image/png")}, "EMPTY_FILE"),
        ({"file": ("notes.txt", b"plain text", "text/plain")}, "UNSUPPORTED_FILE_TYPE"),
        ({"file": ("fake.png", _image_bytes("JPEG"), "image/png")}, "UNSUPPORTED_FILE_TYPE"),
        (
            {"file": ("large.png", b"\x89PNG\r\n\x1a\n" + b"x" * (10 * 1024 * 1024), "image/png")},
            "FILE_TOO_LARGE",
        ),
    ],
)
def test_file_validation_failures(client, files, reason):
    response = client.post("/api/brewery/verify-ocr", files=files)
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "FAILED"
    assert body["ocrSucceeded"] is False
    assert body["verified"] is False
    assert body["documentAssessment"] == "MANUAL_REVIEW"
    assert body["summary"]["reason"] == reason


def test_ocr_processing_failure_hides_internal_error(monkeypatch, client):
    async def mock_extract(*_args, **_kwargs):
        raise RuntimeError("secret provider detail")

    monkeypatch.setattr(main._brewery_ocr, "extract_brewery_info", mock_extract)
    response = client.post(
        "/api/brewery/verify-ocr",
        files={"file": ("license.png", _image_bytes("PNG"), "image/png")},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["summary"]["reason"] == "OCR_PROCESSING_FAILED"
    assert "secret provider detail" not in response.text
