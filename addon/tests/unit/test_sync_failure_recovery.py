"""T034: backup pré-sync + rollback em sincronização interrompida (FR-033, FR-039)."""

import pytest
from anki.collection import Collection

from ankihub_br.db import models as state_db
from ankihub_br.main import backup, sync

NT_ID = "nt-1"


@pytest.fixture
def col(tmp_path):
    collection = Collection(str(tmp_path / "collection.anki2"))
    yield collection
    collection.close()


@pytest.fixture(autouse=True)
def state(tmp_path):
    state_db.init_db(tmp_path / "state.sqlite3")
    yield
    state_db.close_db()


def _payload(notes):
    return {
        "deck_name": "Direito Penal",
        "note_types": [
            {
                "id": NT_ID,
                "name": "Básico BR",
                "field_names": ["Frente", "Verso"],
                "templates": [
                    {"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"}
                ],
                "css": "",
            }
        ],
        "notes": notes,
        "subdecks": [],
        "media": [],
    }


def _note(guid, mod="2026-07-13T00:00:00+00:00", **extra):
    item = {
        "guid": guid,
        "note_type_id": NT_ID,
        "field_values": {"Frente": "Q", "Verso": "A"},
        "tags": [],
        "anki_deck_path": "",
        "mod": mod,
        "deleted": False,
    }
    item.update(extra)
    return item


class FakeClient:
    """Cliente HTTP falso: devolve payloads programados e grava as chamadas."""

    def __init__(self, delta=None, full=None):
        self.delta = delta
        self.full = full
        self.calls = []

    def get_deck_delta(self, deck_id, since_mod=None):
        self.calls.append(("delta", deck_id, since_mod))
        return self.delta

    def get_deck_full(self, deck_id):
        self.calls.append(("full", deck_id))
        return self.full

    def get_media_url(self, content_hash):
        raise AssertionError("sem mídia nestes testes")


def _add_local_note(col, front="local"):
    model = col.models.by_name("Basic") or col.models.all()[0]
    note = col.new_note(model)
    note.fields[0] = front
    col.add_note(note, col.decks.id("Pessoal"))
    return note.id


def test_backup_and_restore_roundtrip(col):
    _add_local_note(col, "antes")

    backup_path = backup.create_backup(col)
    _add_local_note(col, "depois")
    assert col.db.scalar("select count() from notes") == 2

    backup.restore_backup(col, backup_path)

    assert col.db.scalar("select count() from notes") == 1  # FR-039


def test_perform_sync_rolls_back_on_mid_apply_failure(col):
    # a segunda nota referencia um tipo de nota inexistente → falha após a
    # primeira já ter sido aplicada — o rollback deve desfazer TUDO
    broken = _payload([_note("n1"), _note("n2", note_type_id="inexistente")])

    with pytest.raises(KeyError):
        sync.perform_sync(col, FakeClient(delta=broken), "deck-1")

    assert col.models.by_name("Básico BR") is None
    assert col.db.scalar("select count() from notes") == 0
    assert state_db.last_synced_mod("deck-1") is None  # nova tentativa completa


def test_perform_sync_success_records_state_and_uses_since_mod(col):
    client = FakeClient(delta=_payload([_note("n1", mod="2026-07-13T10:00:00+00:00")]))

    sync.perform_sync(col, client, "deck-1")

    assert col.db.scalar("select count() from notes") == 1
    assert state_db.last_synced_mod("deck-1") == "2026-07-13T10:00:00+00:00"

    client.delta = _payload([])
    sync.perform_sync(col, client, "deck-1")
    assert client.calls[-1] == ("delta", "deck-1", "2026-07-13T10:00:00+00:00")


def test_full_resync_fallback_when_server_flags_it(col):
    delta = _payload([])
    delta["full_resync_required"] = True
    client = FakeClient(delta=delta, full=_payload([_note("n1")]))

    sync.perform_sync(col, client, "deck-1")

    assert [c[0] for c in client.calls] == ["delta", "full"]  # FR-035
    assert col.db.scalar("select count() from notes") == 1
