import time

import pytest

from ankihub_br import auth
from ankihub_br.main import constants


class FakeResponse:
    ok = True

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def test_sign_in_uses_supabase_password_grant(monkeypatch):
    calls = []
    session = {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_in": 3600,
    }

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(session)

    monkeypatch.setattr(auth.requests, "post", post)

    assert (
        auth.sign_in(
            "https://project.supabase.co", "public-key", "aluno@example.com", "senha"
        )
        == session
    )
    assert calls == [
        (
            "https://project.supabase.co/auth/v1/token",
            {
                "params": {"grant_type": "password"},
                "headers": {
                    "apikey": "public-key",
                    "Content-Type": "application/json",
                },
                "json": {"email": "aluno@example.com", "password": "senha"},
                "timeout": 15,
            },
        )
    ]


def test_expired_access_token_is_refreshed_and_stored(monkeypatch):
    config = {
        "supabase_url": "https://project.supabase.co",
        "supabase_anon_key": "public-key",
        "token": "expired",
        "refresh_token": "old-refresh",
        "token_expires_at": 1,
    }
    monkeypatch.setattr(
        auth,
        "refresh_session",
        lambda *_args: {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        },
    )

    token, refreshed = auth.ensure_access_token(config)

    assert (token, refreshed) == ("new-access", True)
    assert config["refresh_token"] == "new-refresh"
    assert config["token_expires_at"] > time.time()


def test_auth_rejects_non_https_supabase_url():
    with pytest.raises(auth.AuthError, match="HTTPS"):
        auth.sign_in("http://project.local", "public-key", "a@b.com", "senha")


def test_connection_settings_use_defaults_and_explicit_overrides():
    assert constants.connection_settings({}) == {
        "api_base_url": constants.API_BASE_URL,
        "supabase_url": constants.SUPABASE_URL,
        "supabase_anon_key": constants.SUPABASE_ANON_KEY,
    }
    assert constants.connection_settings(
        {
            "api_base_url": "https://api.example.com",
            "supabase_url": "https://project.example.com",
            "supabase_anon_key": "public-key",
        }
    ) == {
        "api_base_url": "https://api.example.com",
        "supabase_url": "https://project.example.com",
        "supabase_anon_key": "public-key",
    }


def test_sign_out_clears_only_local_session():
    config = {
        "token": "access",
        "refresh_token": "refresh",
        "token_expires_at": 123,
        "api_base_url": "https://api.example.com",
    }

    auth.sign_out(config)

    assert config == {
        "token": "",
        "refresh_token": "",
        "token_expires_at": 0,
        "api_base_url": "https://api.example.com",
    }
