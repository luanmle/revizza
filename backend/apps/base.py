"""Base abstrata de todo modelo do projeto: id UUID + created_at/updated_at (data-model.md)."""

import json
import uuid

from django.db import models


def json_text_forms(text: str) -> list[str]:
    """Formas do texto dentro do JSON persistido, para busca via icontains (FR-007, FR-010).

    sqlite guarda a saída de json.dumps com não-ASCII escapado (\\u00e7); o jsonb do
    Postgres normaliza para o literal UTF-8. Buscar pelas duas formas cobre os dois
    backends sem SQL por vendor.
    """
    forms = [
        json.dumps(text, ensure_ascii=True)[1:-1],
        json.dumps(text, ensure_ascii=False)[1:-1],
    ]
    return list(dict.fromkeys(forms))


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
