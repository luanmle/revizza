"""Autenticação DRF via token JWT emitido pelo Supabase Auth.

O frontend/add-on enviam `Authorization: Bearer <access_token>` do Supabase. Chaves
assimétricas atuais (ES256/RS256) são verificadas via JWKS do projeto
(`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`); tokens HS256 legados só são aceitos
enquanto `SUPABASE_JWT_SECRET` estiver explicitamente configurado. Em ambos os casos
issuer, audience e expiração são validados (T126).
"""

from functools import lru_cache

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions

AUDIENCE = "authenticated"
REQUIRED_CLAIMS = {"require": ["exp", "sub"]}


@lru_cache(maxsize=1)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    # PyJWKClient já cacheia o key set em memória entre requisições
    return jwt.PyJWKClient(jwks_url)


def _issuer() -> str:
    return f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1"


def _decode(token: bytes) -> dict:
    if jwt.get_unverified_header(token).get("alg") == "HS256":
        if not settings.SUPABASE_JWT_SECRET:
            raise jwt.InvalidTokenError("Token HS256 legado não habilitado.")
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience=AUDIENCE,
            issuer=_issuer(),
            options=REQUIRED_CLAIMS,
        )
    signing_key = _jwks_client(
        f"{_issuer()}/.well-known/jwks.json"
    ).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience=AUDIENCE,
        issuer=_issuer(),
        options=REQUIRED_CLAIMS,
    )


class SupabaseAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword.lower().encode():
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Cabeçalho Authorization inválido.")

        try:
            payload = _decode(header[1])
        except (jwt.InvalidTokenError, jwt.PyJWKClientError):
            raise exceptions.AuthenticationFailed("Token inválido ou expirado.")

        from apps.accounts.models import User

        user, _ = User.objects.get_or_create(
            auth_id=payload["sub"],
            defaults={"email": payload.get("email", "")},
        )
        if user.is_suspended:
            # contracts/accounts.md: 403 (não 401) para conta suspensa (FR-049)
            raise exceptions.PermissionDenied("Conta suspensa.")
        return (user, payload)

    def authenticate_header(self, request):
        return self.keyword
