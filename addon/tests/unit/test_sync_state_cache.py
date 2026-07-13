from datetime import datetime

from ankihub_br.db.models import SyncStateCache, close_db, init_db


def test_sync_state_cache_roundtrip(tmp_path):
    init_db(tmp_path / "sync_state.db")
    try:
        mod = datetime(2026, 7, 12, 10, 0, 0)
        SyncStateCache.create(
            deck_id="d1", note_id="n1", last_seen_mod=mod, last_update_type="created"
        )
        # chave composta (deck_id, note_id): replace atualiza em vez de duplicar
        SyncStateCache.replace(
            deck_id="d1", note_id="n1", last_seen_mod=mod, last_update_type="updated"
        ).execute()
        assert SyncStateCache.select().count() == 1
        assert SyncStateCache.get_by_id(("d1", "n1")).last_update_type == "updated"
    finally:
        close_db()
