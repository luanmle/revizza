"""Base abstrata de todo modelo do projeto: id UUID + created_at/updated_at (data-model.md)."""

import json
import uuid

from django.db import models


def json_escaped(text: str) -> str:
    """JSONField persiste não-ASCII escapado (\\u00ea); escapar a agulha da busca igual."""
    return json.dumps(text, ensure_ascii=True)[1:-1]


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
