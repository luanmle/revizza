"""Política de compatibilidade FR-038: apenas a LTS mais recente do Anki Desktop.

Atualizar SUPPORTED_LTS_PREFIX a cada release do add-on (research.md §7) —
o número não é hardcoded na spec justamente porque muda com o tempo.
"""

SUPPORTED_LTS_PREFIX = "26.05"


def anki_version() -> str:
    import anki.buildinfo

    return anki.buildinfo.version


def is_supported_anki() -> bool:
    return anki_version().startswith(SUPPORTED_LTS_PREFIX)


def unsupported_message() -> str:
    return (
        f"Revizza suporta apenas o Anki {SUPPORTED_LTS_PREFIX}.x (LTS). "
        f"Sua versão: {anki_version()}. Atualize o Anki para sincronizar."
    )
