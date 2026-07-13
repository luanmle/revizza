"""Cache local do estado de sincronização por nota (data-model.md, research.md §4).

Vive em user_files/ do add-on, fora do collection.anki2 nativo — nunca replicado ao backend.
"""

from pathlib import Path

from peewee import CharField, CompositeKey, DateTimeField, Model, SqliteDatabase, fn

database = SqliteDatabase(
    None
)  # init adiado — caminho só é conhecido com o perfil aberto


class SyncStateCache(Model):
    deck_id = CharField()
    note_id = CharField()
    last_seen_mod = DateTimeField()
    last_update_type = CharField()  # created | updated | deleted

    class Meta:
        database = database
        primary_key = CompositeKey("deck_id", "note_id")


def init_db(path: str | Path) -> None:
    """Abre (criando se preciso) o SQLite do cache. Chamar em profile_did_open."""
    database.init(str(path))
    database.connect(reuse_if_open=True)
    database.create_tables([SyncStateCache])


def close_db() -> None:
    if not database.is_closed():
        database.close()


def last_synced_mod(deck_id: str) -> str | None:
    """Maior `mod` já aplicado — vira o `?since_mod=` do próximo delta (FR-034)."""
    value = (
        SyncStateCache.select(fn.MAX(SyncStateCache.last_seen_mod))
        .where(SyncStateCache.deck_id == str(deck_id))
        .scalar()
    )
    if value is None or isinstance(value, str):
        return value
    return value.isoformat()  # peewee devolve datetime; a API espera ISO 8601


def record_synced_notes(deck_id: str, note_items: list[dict]) -> None:
    for item in note_items:
        if item.get("deleted"):
            update_type = "deleted"
        elif SyncStateCache.get_or_none(
            SyncStateCache.deck_id == str(deck_id),
            SyncStateCache.note_id == item["guid"],
        ):
            update_type = "updated"
        else:
            update_type = "created"
        SyncStateCache.insert(
            deck_id=str(deck_id),
            note_id=item["guid"],
            last_seen_mod=item["mod"],
            last_update_type=update_type,
        ).on_conflict_replace().execute()
