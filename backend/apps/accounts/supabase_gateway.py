"""Ponte fina com o Supabase Auth (research.md §6).

Cadastro e recuperação de senha são delegados ao Supabase (que envia os e-mails
transacionais); isolado num módulo para os testes trocarem por monkeypatch sem rede.
"""

from functools import lru_cache

from django.conf import settings
from supabase import create_client


@lru_cache(maxsize=1)
def _client():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def sign_up(email: str, password: str) -> str:
    """Cria o usuário no Supabase Auth (dispara e-mail de verificação); retorna o auth_id."""
    response = _client().auth.sign_up({"email": email, "password": password})
    return str(response.user.id)


def send_password_reset(email: str, redirect_to: str) -> None:
    _client().auth.reset_password_for_email(email, {"redirect_to": redirect_to})


def delete_user(auth_id: str) -> None:
    """Exclusão administrativa; service role fica somente no backend."""
    _client().auth.admin.delete_user(str(auth_id))
