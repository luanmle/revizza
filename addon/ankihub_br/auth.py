"""Supabase Auth REST client kept small for add-on vendoring."""

import time
from urllib.parse import urlparse

import requests


class AuthError(RuntimeError):
    pass


def _token_request(
    supabase_url: str, anon_key: str, grant_type: str, payload: dict
) -> dict:
    parsed = urlparse(supabase_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise AuthError("A URL do Supabase deve usar HTTPS.")
    if not anon_key:
        raise AuthError("Informe a chave pública (anon/publishable) do Supabase.")

    response = requests.post(
        f"{supabase_url.rstrip('/')}/auth/v1/token",
        params={"grant_type": grant_type},
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    data = response.json()
    if not response.ok:
        detail = (
            data.get("error_description")
            or data.get("msg")
            or data.get("message")
            or "Credenciais inválidas."
        )
        raise AuthError(f"Não foi possível entrar: {detail}")
    if not data.get("access_token") or not data.get("refresh_token"):
        raise AuthError("O Supabase retornou uma sessão incompleta.")
    return data


def sign_in(supabase_url: str, anon_key: str, email: str, password: str) -> dict:
    return _token_request(
        supabase_url,
        anon_key,
        "password",
        {"email": email.strip(), "password": password},
    )


def refresh_session(supabase_url: str, anon_key: str, refresh_token: str) -> dict:
    return _token_request(
        supabase_url,
        anon_key,
        "refresh_token",
        {"refresh_token": refresh_token},
    )


def store_session(config: dict, session: dict) -> None:
    config["token"] = session["access_token"]
    config["refresh_token"] = session["refresh_token"]
    config["token_expires_at"] = int(
        session.get("expires_at") or time.time() + session.get("expires_in", 3600)
    )


def ensure_access_token(config: dict) -> tuple[str, bool]:
    token = config.get("token", "")
    expires_at = int(config.get("token_expires_at") or 0)
    if token and (not expires_at or expires_at > time.time() + 60):
        return token, False
    refresh_token = config.get("refresh_token", "")
    if not refresh_token:
        raise AuthError("Faça login no add-on antes de sincronizar.")
    session = refresh_session(
        config.get("supabase_url", ""),
        config.get("supabase_anon_key", ""),
        refresh_token,
    )
    store_session(config, session)
    return config["token"], True

