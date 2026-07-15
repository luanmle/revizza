"""US1: botão "Ver no Revizza" só aparece quando o GUID está no cache (FR-001)."""

import sys
from types import SimpleNamespace

from ankihub_br.db.models import SyncStateCache, close_db, init_db
from ankihub_br.gui import reviewer


def _card(guid):
    return SimpleNamespace(note=lambda: SimpleNamespace(guid=guid))


def _seed(tmp_path, guid, deck_id="d1"):
    init_db(tmp_path / "sync_state.db")
    SyncStateCache.create(
        deck_id=deck_id,
        note_id=guid,
        last_seen_mod="2026-07-12T10:00:00",
        last_update_type="created",
    )


def test_visible_only_when_guid_in_cache(tmp_path):
    _seed(tmp_path, "guid-known")
    try:
        assert reviewer.is_action_visible(_card("guid-known")) is True
        assert reviewer.is_action_visible(_card("guid-unknown")) is False
        assert reviewer.is_action_visible(None) is False
    finally:
        close_db()


def test_reviewer_shown_injects_button_only_when_visible(tmp_path, monkeypatch):
    _seed(tmp_path, "guid-known")
    evals = []
    fake_mw = SimpleNamespace(
        reviewer=SimpleNamespace(
            bottom=SimpleNamespace(web=SimpleNamespace(eval=evals.append))
        )
    )
    monkeypatch.setitem(sys.modules, "aqt", SimpleNamespace(mw=fake_mw))
    try:
        reviewer._on_reviewer_shown(_card("guid-unknown"))
        assert evals == []  # escondido: nenhuma injeção

        reviewer._on_reviewer_shown(_card("guid-known"))
        assert len(evals) == 1
        assert "revizza:view" in evals[0]
    finally:
        close_db()


def test_js_message_view_opens_note_url(tmp_path, monkeypatch):
    _seed(tmp_path, "guid-known")
    opened = []
    fake_mw = SimpleNamespace(
        reviewer=SimpleNamespace(card=_card("guid-known")),
        addonManager=SimpleNamespace(
            getConfig=lambda _pkg: {"api_base_url": "https://api.test/api/v1"}
        ),
    )
    monkeypatch.setitem(sys.modules, "aqt", SimpleNamespace(mw=fake_mw))
    monkeypatch.setitem(
        sys.modules, "aqt.utils", SimpleNamespace(openLink=opened.append)
    )
    try:
        handled, payload = reviewer._on_js_message((False, None), "revizza:view", None)
        assert handled is True
        assert opened == ["https://api.test/api/v1/go/note/guid-known/"]

        # mensagem não-Revizza passa adiante intacta
        assert reviewer._on_js_message((False, None), "other:msg", None) == (
            False,
            None,
        )
    finally:
        close_db()
