"""Cache local do estado de sincronização por nota (data-model.md, research.md §4).

Vive em user_files/ do add-on, fora do collection.anki2 nativo — nunca replicado ao backend.
"""

import hashlib
import json
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
    field_hash = CharField(null=True)  # baseline do Note Content (US2 pre-check)

    class Meta:
        database = database
        primary_key = CompositeKey("deck_id", "note_id")


def field_content_hash(field_values: dict) -> str:
    """Hash estável do Note Content (só campos). Base do pre-check "nada a sugerir".

    ponytail: hash do conteúdo web sincronizado; campos protegidos ficam locais e
    não entram aqui — troca por hash pós-merge se protegidos passarem a divergir.
    """
    canonical = json.dumps(field_values, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def init_db(path: str | Path) -> None:
    """Abre (criando se preciso) o SQLite do cache. Chamar em profile_did_open."""
    database.init(str(path))
    database.connect(reuse_if_open=True)
    database.create_tables([SyncStateCache])
    _ensure_field_hash_column()


def _ensure_field_hash_column() -> None:
    """Migração aditiva: caches antigos não têm field_hash (nunca destrói dados)."""
    columns = {column.name for column in database.get_columns("syncstatecache")}
    if "field_hash" not in columns:
        database.execute_sql("ALTER TABLE syncstatecache ADD COLUMN field_hash VARCHAR")


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


def deck_id_for_guid(guid: str) -> str | None:
    """Deck do GUID se a nota está no cache e não foi deletada (regra de visibilidade)."""
    row = SyncStateCache.get_or_none(
        (SyncStateCache.note_id == str(guid))
        & (SyncStateCache.last_update_type != "deleted")
    )
    return row.deck_id if row else None


def field_hash_for_guid(guid: str) -> str | None:
    """Baseline do Note Content da nota (None se ausente ou deletada)."""
    row = SyncStateCache.get_or_none(
        (SyncStateCache.note_id == str(guid))
        & (SyncStateCache.last_update_type != "deleted")
    )
    return row.field_hash if row else None


def record_synced_notes(deck_id: str, note_items: list[dict]) -> None:
    for item in note_items:
        if item.get("deleted"):
            update_type = "deleted"
            hash_value = None
        else:
            hash_value = field_content_hash(item["field_values"])
            if SyncStateCache.get_or_none(
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
            field_hash=hash_value,
        ).on_conflict_replace().execute()
