"""Autenticação DRF via token JWT emitido pelo Supabase Auth.

O frontend/add-on enviam `Authorization: Bearer <access_token>` do Supabase; aqui o token é
verificado localmente com o JWT secret do projeto (HS256), sem round-trip ao servidor de Auth.
"""

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions


class SupabaseAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword.lower().encode():
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Cabeçalho Authorization inválido.")

        try:
            payload = jwt.decode(
                header[1],
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except jwt.InvalidTokenError:
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
