"""Contract test: GET /accounts/me/ e PATCH /accounts/me/consents/ (contracts/accounts.md)."""

import time
import uuid

import jwt
import pytest

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

ME_URL = "/api/v1/accounts/me/"
CONSENTS_URL = "/api/v1/accounts/me/consents/"


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
