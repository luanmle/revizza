"""Integração US1: cadastro → login (token Supabase) → alterar consentimento (spec US1)."""

import time
import uuid

import jwt
import pytest

pytestmark = pytest.mark.django_db


def test_register_login_and_toggle_consent(api_client, settings, monkeypatch):
    settings.SUPABASE_JWT_SECRET = "test-secret"
    settings.SUPABASE_URL = "https://test.supabase.co"
    auth_id = str(uuid.uuid4())
    monkeypatch.setattr(
        "apps.accounts.supabase_gateway.sign_up", lambda email, password: auth_id
    )

    # 1. cadastro
    response = api_client.post(
        "/api/v1/accounts/register/",
        {"email": "fluxo@example.com", "password": "s3nha-forte"},
        format="json",
    )
    assert response.status_code == 201

    # 2. "login": Supabase emite o JWT; a API só o verifica (FR-002)
    token = jwt.encode(
        {
            "sub": auth_id,
            "email": "fluxo@example.com",
            "aud": "authenticated",
            "iss": "https://test.supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
        },
        "test-secret",
        algorithm="HS256",
    )
    auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    me = api_client.get("/api/v1/accounts/me/", **auth)
    assert me.status_code == 200
    assert me.json()["consent_research_data"] is False

    # 3. alterar consentimento com efeito imediato (FR-045)
    patched = api_client.patch(
        "/api/v1/accounts/me/consents/",
        {"consent_research_data": True},
        format="json",
        **auth,
    )
    assert patched.status_code == 200

    assert (
        api_client.get("/api/v1/accounts/me/", **auth).json()["consent_research_data"]
        is True
    )
