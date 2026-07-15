from ankihub_br.gui import connection_status_message, menu_item_states


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
