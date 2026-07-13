"""Registra hooks/monkey-patch na inicialização do Anki (T043, research.md §5)."""


def run() -> None:
    try:
        from aqt import mw
    except ImportError:  # fora do Anki (testes headless, ferramentas)
        return
    if mw is None:  # aqt importado sem a aplicação rodando
        return
    from .gui import setup

    setup()
