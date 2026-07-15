from ankihub_br import auth
from ankihub_br.gui import (
    connection_status_message,
    deck_group_title,
    menu_item_states,
    sync_failure_message,
)


def test_menu_items_follow_session_state():
    assert menu_item_states(False) == (
        ("Entrar", True),
        ("Sincronizar agora", False),
        ("Decks inscritos", False),
        ("Criar deck Revizza", False),
        ("Testar conexão", True),
    )
    assert menu_item_states(True) == (
        ("Sair", True),
        ("Sincronizar agora", True),
        ("Decks inscritos", True),
        ("Criar deck Revizza", True),
        ("Testar conexão", True),
    )


def test_menu_item_states_shows_pending_count():
    assert menu_item_states(True, pending_count=2) == (
        ("Sair", True),
        ("Sincronizar agora", True),
        ("Decks inscritos (2)", True),
        ("Criar deck Revizza", True),
        ("Testar conexão", True),
    )
    assert menu_item_states(True, pending_count=0) == (
        ("Sair", True),
        ("Sincronizar agora", True),
        ("Decks inscritos", True),
        ("Criar deck Revizza", True),
        ("Testar conexão", True),
    )


def test_deck_group_title_marks_pending_sync():
    assert deck_group_title({"name": "Direito", "pending_sync": True}) == (
        "Direito ⚠ pendente"
    )
    assert deck_group_title({"name": "Direito", "pending_sync": False}) == "Direito"
    assert deck_group_title({"name": "Direito"}) == "Direito"


def test_sync_failure_message_distinguishes_auth_error_from_collection_failure():
    auth_msg = sync_failure_message(auth.AuthError("Invalid Refresh Token: Refresh Token Not Found"))
    assert "restaurada do backup" not in auth_msg  # nenhum backup foi tocado (bug: invalid-refresh-token)
    assert "Faça login novamente" in auth_msg

    collection_msg = sync_failure_message(RuntimeError("boom"))
    assert "restaurada do backup" in collection_msg
    assert "boom" in collection_msg


def test_connection_status_keeps_api_and_session_signals_distinct():
    assert connection_status_message({"api_ok": False, "session_ok": None}) == (
        "API indisponível"
    )
    assert connection_status_message({"api_ok": True, "session_ok": False}) == (
        "API ok\nSessão expirada"
    )
    assert connection_status_message({"api_ok": True, "session_ok": True}) == (
        "API ok\nSessão ok"
    )
