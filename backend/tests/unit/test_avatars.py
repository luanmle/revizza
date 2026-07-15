"""Validação de upload de avatar (data-model.md regras 1-3, FR-002/FR-003)."""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.exceptions import ValidationError

from apps.accounts import avatars


def _image_file(fmt="JPEG", size=(10, 10), name="avatar.jpg"):
    buffer = BytesIO()
    Image.new("RGB", size, color="red").save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def test_accepts_valid_small_jpeg():
    content, ext = avatars.validate_and_decode(_image_file("JPEG"))
    assert ext == "jpg"
    assert content


def test_accepts_valid_small_png():
    content, ext = avatars.validate_and_decode(_image_file("PNG", name="avatar.png"))
    assert ext == "png"


def test_rejects_non_image_bytes():
    bogus = SimpleUploadedFile("avatar.jpg", b"not an image", content_type="image/jpeg")
    with pytest.raises(ValidationError):
        avatars.validate_and_decode(bogus)


def test_rejects_oversized_file():
    big = SimpleUploadedFile(
        "avatar.jpg", b"0" * (avatars.MAX_UPLOAD_BYTES + 1), content_type="image/jpeg"
    )
    with pytest.raises(ValidationError):
        avatars.validate_and_decode(big)


def test_rejects_oversized_dimensions():
    huge = _image_file(
        "JPEG", size=(avatars.MAX_DIMENSION_PX + 1, avatars.MAX_DIMENSION_PX + 1)
    )
    with pytest.raises(ValidationError):
        avatars.validate_and_decode(huge)
