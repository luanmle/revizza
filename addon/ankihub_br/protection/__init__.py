"""Preserva conteúdo pessoal durante a sincronização web → Anki (FR-040 a FR-044)."""

FIELD_TAG_PREFIX = "AnkiHubBR_Protect::"
INTERNAL_TAGS = frozenset({"leech", "marked"})


def protected_field_names(
    local_tags: list[str], configured_fields: set[str]
) -> set[str]:
    per_note = {
        tag.removeprefix(FIELD_TAG_PREFIX)
        for tag in local_tags
        if tag.startswith(FIELD_TAG_PREFIX) and tag != FIELD_TAG_PREFIX
    }
    return set(configured_fields) | per_note


def merge_tags(
    official_tags: list[str], local_tags: list[str], configured_tags: set[str]
) -> list[str]:
    configured = set(configured_tags)
    preserved = [
        tag
        for tag in local_tags
        if tag in configured
        or tag.casefold() in INTERNAL_TAGS
        or tag.startswith(FIELD_TAG_PREFIX)
    ]
    return list(dict.fromkeys([*official_tags, *preserved]))
