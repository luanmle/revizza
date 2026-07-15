"""Contract test: GET/PATCH /accounts/me/ e PATCH /accounts/me/consents/ (contracts/accounts.md,
contracts/accounts-api.md)."""

import time
import uuid
from io import BytesIO

import jwt
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

ME_URL = "/api/v1/accounts/me/"
CONSENTS_URL = "/api/v1/accounts/me/consents/"


def _image_bytes(fmt="JPEG"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def fake_avatar_storage(monkeypatch):
    """Substitui apps.accounts.avatars por um storage em memória (sem rede/Supabase)."""
    store: dict[str, bytes] = {}

    def fake_upload(user_id, content, ext):
        path = f"{user_id}/fake.{ext}"
        store[path] = content
        return path

    def fake_delete(path):
        store.pop(path, None)

    def fake_public_url(path):
        return f"https://fake.supabase.co/storage/v1/object/public/avatars/{path}" if path else None

    monkeypatch.setattr("apps.accounts.views.avatars.upload", fake_upload)
    monkeypatch.setattr("apps.accounts.views.avatars.delete", fake_delete)
    monkeypatch.setattr("apps.accounts.serializers.avatars.public_url", fake_public_url)
    return store


def test_me_returns_profile(auth_client, user):
    response = auth_client.get(ME_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == ""
    assert body["email"] == user.email
    assert body["consent_marketing_emails"] is False
    assert body["consent_research_data"] is False
    assert "target_career" in body and "target_board" in body


def test_me_requires_authentication(api_client):
    assert api_client.get(ME_URL).status_code == 401


def test_patch_consents_has_immediate_effect(auth_client, user):
    response = auth_client.patch(
        CONSENTS_URL, {"consent_marketing_emails": True}, format="json"
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.consent_marketing_emails is True
    assert user.consent_research_data is False  # não tocado pelo PATCH parcial


def test_patch_me_updates_optional_display_name(auth_client, user):
    response = auth_client.patch(ME_URL, {"name": "Ana Souza"}, format="json")

    assert response.status_code == 200
    assert response.json()["name"] == "Ana Souza"
    user.refresh_from_db()
    assert user.name == "Ana Souza"


def test_patch_me_uploads_valid_avatar(auth_client, user, fake_avatar_storage):
    upload = SimpleUploadedFile(
        "avatar.jpg", _image_bytes("JPEG"), content_type="image/jpeg"
    )

    response = auth_client.patch(ME_URL, {"avatar": upload}, format="multipart")

    assert response.status_code == 200
    assert response.json()["avatar_url"]
    user.refresh_from_db()
    assert user.avatar_path

    fetched = auth_client.get(ME_URL)
    assert fetched.json()["avatar_url"] == response.json()["avatar_url"]


def test_patch_me_returns_clean_error_when_storage_upload_fails(
    auth_client, user, monkeypatch
):
    """Storage indisponível/bucket ausente não deve virar 500 (bug avatar-upload-fails)."""

    def boom(user_id, content, ext):
        raise RuntimeError("bucket not found")

    monkeypatch.setattr("apps.accounts.views.avatars.upload", boom)
    upload = SimpleUploadedFile(
        "avatar.jpg", _image_bytes("JPEG"), content_type="image/jpeg"
    )

    response = auth_client.patch(ME_URL, {"avatar": upload}, format="multipart")

    assert response.status_code == 400
    assert response.json()["avatar"]
    user.refresh_from_db()
    assert user.avatar_path is None


def test_patch_me_returns_clean_error_when_storage_delete_fails(
    auth_client, user, fake_avatar_storage, monkeypatch
):
    upload = SimpleUploadedFile(
        "avatar.jpg", _image_bytes("JPEG"), content_type="image/jpeg"
    )
    auth_client.patch(ME_URL, {"avatar": upload}, format="multipart")
    user.refresh_from_db()
    existing_path = user.avatar_path

    def boom(path):
        raise RuntimeError("storage unreachable")

    monkeypatch.setattr("apps.accounts.views.avatars.delete", boom)

    response = auth_client.patch(ME_URL, {"avatar": None}, format="json")

    assert response.status_code == 400
    assert response.json()["avatar"]
    user.refresh_from_db()
    assert user.avatar_path == existing_path  # inalterado (FR-003)


def test_patch_me_rejects_non_image_upload(auth_client, user, fake_avatar_storage):
    upload = SimpleUploadedFile(
        "avatar.jpg", b"not an image", content_type="image/jpeg"
    )

    response = auth_client.patch(ME_URL, {"avatar": upload}, format="multipart")

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.avatar_path is None


def test_patch_me_rejects_oversized_avatar(auth_client, user, fake_avatar_storage):
    from apps.accounts import avatars

    upload = SimpleUploadedFile(
        "avatar.jpg",
        b"0" * (avatars.MAX_UPLOAD_BYTES + 1),
        content_type="image/jpeg",
    )

    response = auth_client.patch(ME_URL, {"avatar": upload}, format="multipart")

    assert response.status_code == 400


def test_patch_me_name_only_leaves_other_fields_unchanged(
    auth_client, user, fake_avatar_storage
):
    upload = SimpleUploadedFile(
        "avatar.jpg", _image_bytes("JPEG"), content_type="image/jpeg"
    )
    auth_client.patch(ME_URL, {"avatar": upload}, format="multipart")
    auth_client.patch(
        ME_URL, {"target_career": "fiscal", "target_board": "TJ-SP"}, format="json"
    )
    before = auth_client.get(ME_URL).json()

    response = auth_client.patch(ME_URL, {"name": "Novo Nome"}, format="json")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Novo Nome"
    assert body["avatar_url"] == before["avatar_url"]
    assert body["target_career"] == before["target_career"]
    assert body["target_board"] == before["target_board"]


def test_patch_me_removes_avatar(auth_client, user, fake_avatar_storage):
    upload = SimpleUploadedFile(
        "avatar.jpg", _image_bytes("JPEG"), content_type="image/jpeg"
    )
    auth_client.patch(ME_URL, {"avatar": upload}, format="multipart")

    response = auth_client.patch(ME_URL, {"avatar": None}, format="json")

    assert response.status_code == 200
    assert response.json()["avatar_url"] is None
    user.refresh_from_db()
    assert user.avatar_path is None


def test_patch_me_updates_target_career_and_board(auth_client, user):
    response = auth_client.patch(
        ME_URL, {"target_career": "policial", "target_board": "TJ-SP"}, format="json"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["target_career"] == "policial"
    assert body["target_board"] == "TJ-SP"

    fetched = auth_client.get(ME_URL).json()
    assert fetched["target_career"] == "policial"
    assert fetched["target_board"] == "TJ-SP"


def test_patch_me_rejects_invalid_target_career(auth_client, user):
    response = auth_client.patch(
        ME_URL, {"target_career": "not-a-real-choice"}, format="json"
    )

    assert response.status_code == 400


def test_suspended_user_gets_403(api_client, settings, db):
    # força o caminho real de autenticação (não force_authenticate) para validar o soft-ban
    settings.SUPABASE_JWT_SECRET = "test-secret"
    settings.SUPABASE_URL = "https://test.supabase.co"
    suspended = User.objects.create(
        auth_id=uuid.uuid4(), email="banido@example.com", is_suspended=True
    )
    token = jwt.encode(
        {
            "sub": str(suspended.auth_id),
            "email": suspended.email,
            "aud": "authenticated",
            "iss": "https://test.supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
        },
        "test-secret",
        algorithm="HS256",
    )

    response = api_client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {token}")

    assert response.status_code == 403
