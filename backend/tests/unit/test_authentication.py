"""T126: verificação JWKS (ES256) com issuer/audience/exp + compatibilidade HS256 legada."""

import time
import uuid
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from rest_framework.test import APIRequestFactory

from config import authentication
from config.authentication import SupabaseAuthentication

pytestmark = pytest.mark.django_db

ISSUER = "https://test.supabase.co/auth/v1"


@pytest.fixture
def ec_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def supabase_settings(settings):
    settings.SUPABASE_URL = "https://test.supabase.co"
    settings.SUPABASE_JWT_SECRET = ""
    return settings


@pytest.fixture
def jwks(ec_key, monkeypatch):
    """Substitui o fetch de rede do JWKS pela chave pública do teste."""
    signing_key = SimpleNamespace(key=ec_key.public_key())
    monkeypatch.setattr(
        authentication,
        "_jwks_client",
        lambda url: SimpleNamespace(get_signing_key_from_jwt=lambda token: signing_key),
    )


def _claims(**overrides):
    claims = {
        "sub": str(uuid.uuid4()),
        "email": "jwks@example.com",
        "aud": "authenticated",
        "iss": ISSUER,
        "exp": int(time.time()) + 3600,
    }
    claims.update(overrides)
    return claims


def _authenticate(token):
    request = APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
    return SupabaseAuthentication().authenticate(request)


def test_es256_token_via_jwks_is_accepted(supabase_settings, jwks, ec_key):
    token = jwt.encode(_claims(), ec_key, algorithm="ES256")

    user, payload = _authenticate(token)

    assert str(user.auth_id) == payload["sub"]


@pytest.mark.parametrize(
    "bad_claims",
    [
        {"exp": int(time.time()) - 10},  # expirado
        {"iss": "https://malicioso.example.com/auth/v1"},  # issuer errado
        {"aud": "outra-audiencia"},  # audience errada
    ],
)
def test_invalid_es256_claims_are_rejected(supabase_settings, jwks, ec_key, bad_claims):
    from rest_framework.exceptions import AuthenticationFailed

    token = jwt.encode(_claims(**bad_claims), ec_key, algorithm="ES256")

    with pytest.raises(AuthenticationFailed):
        _authenticate(token)


def test_legacy_hs256_requires_explicit_secret(supabase_settings):
    from rest_framework.exceptions import AuthenticationFailed

    token = jwt.encode(_claims(), "legacy-secret", algorithm="HS256")

    # sem SUPABASE_JWT_SECRET configurado, HS256 legado é recusado
    with pytest.raises(AuthenticationFailed):
        _authenticate(token)

    supabase_settings.SUPABASE_JWT_SECRET = "legacy-secret"
    user, payload = _authenticate(token)
    assert str(user.auth_id) == payload["sub"]
