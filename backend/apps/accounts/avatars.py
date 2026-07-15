"""Validação e storage de avatar de perfil (data-model.md, FR-002/FR-003/FR-011).

Isolado num módulo próprio (mirrors apps/sync/media.py) para os testes trocarem por
monkeypatch sem rede; bucket é público (research.md) ao contrário de `media`.
"""

import hashlib
from functools import lru_cache

from django.conf import settings
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers
from supabase import create_client

BUCKET = "avatars"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_DIMENSION_PX = 4096
ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


@lru_cache(maxsize=1)
def _storage():
    return create_client(
        settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
    ).storage


def validate_and_decode(uploaded_file) -> tuple[bytes, str]:
    """Decodifica e valida a imagem de fato (nunca confia em Content-Type/extensão do client).

    Retorna (bytes originais, extensão do formato). Levanta ValidationError com mensagem
    legível em qualquer falha, sem persistir nada.
    """
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise serializers.ValidationError(
            "Arquivo maior que o limite de 5MB."
        )
    content = uploaded_file.read()
    try:
        image = Image.open(uploaded_file)
        image.verify()
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image_format = image.format
        width, height = image.size
    except (UnidentifiedImageError, OSError):
        raise serializers.ValidationError("Formato de imagem não suportado.")
    if image_format not in ALLOWED_FORMATS:
        raise serializers.ValidationError("Formato de imagem não suportado.")
    if width > MAX_DIMENSION_PX or height > MAX_DIMENSION_PX:
        raise serializers.ValidationError(
            f"Dimensões da imagem excedem o limite de {MAX_DIMENSION_PX}x{MAX_DIMENSION_PX}px."
        )
    return content, ALLOWED_FORMATS[image_format]


def upload(user_id, content: bytes, ext: str) -> str:
    content_hash = hashlib.sha256(content).hexdigest()
    path = f"{user_id}/{content_hash}.{ext}"
    _storage().from_(BUCKET).upload(
        path, content, {"content-type": f"image/{ext}", "upsert": "true"}
    )
    return path


def delete(storage_path: str) -> None:
    _storage().from_(BUCKET).remove([storage_path])


def public_url(storage_path: str | None) -> str | None:
    if not storage_path:
        return None
    return _storage().from_(BUCKET).get_public_url(storage_path)
