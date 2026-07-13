"""Sanitização de HTML de campos rich-text via nh3 (FR-015, research.md §2).

Allowlist restrita ao que o Anki nativamente aceita em campos: formatação básica, listas,
links, `<span style>` (tamanho de fonte) e `<img>` para mídia já referenciada. Nunca confiar
na sanitização client-side — todo HTML passa por aqui antes de persistir.
"""

import nh3

_ALLOWED_TAGS = {
    "b",
    "strong",
    "i",
    "em",
    "u",
    "s",
    "del",
    "ul",
    "ol",
    "li",
    "a",
    "span",
    "img",
    "br",
    "div",
    "p",
    "sub",
    "sup",
}

_ALLOWED_ATTRIBUTES = {
    "a": {"href"},
    "img": {"src"},
    "span": {"style"},
    "div": {"style"},
}

_ALLOWED_URL_SCHEMES = {"http", "https"}


def sanitize_html(html: str) -> str:
    return nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer",
    )


def sanitize_field_values(field_values: dict[str, str]) -> dict[str, str]:
    """Sanitiza o JSON `{nome_campo: html}` de uma Note/Suggestion inteira."""
    return {field: sanitize_html(value) for field, value in field_values.items()}
