"""URLs pré-assinadas do Supabase Storage para mídia (FR-036, T038).

Isolado num módulo para os testes trocarem por monkeypatch sem rede.
"""

from functools import lru_cache

from django.conf import settings
from supabase import create_client

BUCKET = "media"
SIGNED_URL_TTL_SECONDS = 3600


@lru_cache(maxsize=1)
def _storage():
    return create_client(
        settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
    ).storage


def signed_download_url(storage_path: str) -> str:
    result = (
        _storage().from_(BUCKET).create_signed_url(storage_path, SIGNED_URL_TTL_SECONDS)
    )
    return result["signedURL"]


def signed_upload_url(storage_path: str) -> str:
    result = _storage().from_(BUCKET).create_signed_upload_url(storage_path)
    return result["signed_url"]
