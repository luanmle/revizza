"""Sincronização unidirecional web → Anki local (FR-031 a FR-039).

O delta é aplicado na ordem fixa: tipos de nota → notas → reorganização de
subdecks (FR-034). O formato do payload é o de `_deck_payload` no backend
(apps/sync/views.py): deck_name, note_types, notes, subdecks, media.
"""

import time

from ..db import models as state
from ..protection import merge_tags, protected_field_names
from . import backup as backup_mod
from . import media as media_mod

MIN_SYNC_INTERVAL_SECONDS = 10  # FR-032 (guarda local; o backend também responde 429)
REMOVED_TAG = "AnkiHubBR_Removida"  # FR-037: marcar preservando o histórico local

_last_sync_started_at = float("-inf")
_sync_in_progress = False


class FullResyncRequired(Exception):
    """Delta estruturalmente irreconciliável — repuxar o deck inteiro (FR-035)."""


def can_sync_now() -> bool:
    """Guarda de 10s por *execução* de sync (todas as assinaturas de uma vez)."""
    return not _sync_in_progress and (
        time.monotonic() - _last_sync_started_at >= MIN_SYNC_INTERVAL_SECONDS
    )


def mark_sync_started() -> None:
    global _last_sync_started_at, _sync_in_progress
    _last_sync_started_at = time.monotonic()
    _sync_in_progress = True


def mark_sync_finished() -> None:
    global _sync_in_progress
    _sync_in_progress = False


def _note_id_by_guid(col, guid: str):
    return col.db.scalar("select id from notes where guid = ?", guid)


def _default_qfmt(note_type: dict) -> str:
    return "{{%s}}" % note_type["field_names"][0]


def _default_afmt(note_type: dict) -> str:
    answer = note_type["field_names"][1 if len(note_type["field_names"]) > 1 else 0]
    return "{{FrontSide}}\n<hr id=answer>\n{{%s}}" % answer


def _build_template(col, note_type: dict, template: dict) -> dict:
    built = col.models.new_template(template.get("name", "Card"))
    built["qfmt"] = template.get("qfmt") or _default_qfmt(note_type)
    built["afmt"] = template.get("afmt") or _default_afmt(note_type)
    return built


def _apply_note_types(col, note_types: list[dict], *, allow_structural: bool) -> dict:
    """Fase 1 (FR-034). Retorna {id_remoto: notetype_local}."""
    mapping = {}
    for note_type in note_types:
        model = col.models.by_name(note_type["name"])
        if model is None:
            model = col.models.new(note_type["name"])
            for field_name in note_type["field_names"]:
                col.models.add_field(model, col.models.new_field(field_name))
            for template in note_type["templates"]:
                col.models.add_template(
                    model, _build_template(col, note_type, template)
                )
            if note_type.get("css"):
                model["css"] = note_type["css"]
            col.models.add(model)
            model = col.models.by_name(note_type["name"])
        else:
            if len(model["tmpls"]) != len(note_type["templates"]):
                if not allow_structural:
                    raise FullResyncRequired(note_type["name"])
                while len(model["tmpls"]) > len(note_type["templates"]):
                    col.models.remove_template(model, model["tmpls"][-1])
                while len(model["tmpls"]) < len(note_type["templates"]):
                    extra = note_type["templates"][len(model["tmpls"])]
                    col.models.add_template(
                        model, _build_template(col, note_type, extra)
                    )
            local_field_names = [f["name"] for f in model["flds"]]
            for field_name in note_type["field_names"]:
                if field_name not in local_field_names:
                    # campos só são acrescentados, nunca reordenados (data-model.md)
                    col.models.add_field(model, col.models.new_field(field_name))
            for local_template, remote_template in zip(
                model["tmpls"], note_type["templates"]
            ):
                local_template["name"] = remote_template.get(
                    "name", local_template["name"]
                )
                local_template["qfmt"] = (
                    remote_template.get("qfmt") or local_template["qfmt"]
                )
                local_template["afmt"] = (
                    remote_template.get("afmt") or local_template["afmt"]
                )
            if note_type.get("css"):
                model["css"] = note_type["css"]
            col.models.update_dict(model)
            model = col.models.by_name(note_type["name"])
        mapping[note_type["id"]] = model
    return mapping


def _fill_fields(
    note,
    field_names: list[str],
    field_values: dict,
    protected_fields: set[str] | None = None,
) -> None:
    protected_fields = protected_fields or set()
    for index, field_name in enumerate(field_names):
        if (
            field_name in field_values
            and field_name not in protected_fields
            and index < len(note.fields)
        ):
            note.fields[index] = field_values[field_name]


def _remove_or_mark(col, note_id, *, delete_notes_on_removal: bool) -> None:
    if delete_notes_on_removal:
        col.remove_notes([note_id])
        return
    note = col.get_note(note_id)
    if REMOVED_TAG not in note.tags:
        note.tags.append(REMOVED_TAG)
        col.update_note(note)


def _apply_notes(
    col,
    deck_name: str,
    note_items: list[dict],
    models_by_remote_id: dict,
    *,
    delete_notes_on_removal: bool,
    protected_fields: set[str],
    protected_tags: set[str],
) -> None:
    """Fase 2 (FR-034). Cria/atualiza/remove notas pelo guid."""
    root_deck_id = col.decks.id(deck_name)
    for item in note_items:
        note_id = _note_id_by_guid(col, item["guid"])
        if item.get("deleted"):
            if note_id:  # FR-037: preferência do assinante
                _remove_or_mark(
                    col, note_id, delete_notes_on_removal=delete_notes_on_removal
                )
            continue
        model = models_by_remote_id[item["note_type_id"]]
        field_names = [f["name"] for f in model["flds"]]
        if note_id:
            note = col.get_note(note_id)
            fields_to_keep = protected_field_names(note.tags, protected_fields)
            _fill_fields(note, field_names, item["field_values"], fields_to_keep)
            note.tags = merge_tags(item["tags"], note.tags, protected_tags)
            col.update_note(note)
        else:
            note = col.new_note(model)
            _fill_fields(note, field_names, item["field_values"])
            note.tags = list(item["tags"])
            note.guid = item["guid"]
            col.add_note(note, root_deck_id)


def _apply_subdeck_moves(col, deck_name: str, note_items: list[dict]) -> None:
    """Fase 3 (FR-034). Move os cards para o subdeck indicado pelo payload."""
    for item in note_items:
        if item.get("deleted"):
            continue
        target = deck_name
        if item.get("anki_deck_path"):
            target = f"{deck_name}::{item['anki_deck_path']}"
        deck_id = col.decks.id(target)
        note_id = _note_id_by_guid(col, item["guid"])
        col.set_deck(col.card_ids_of_note(note_id), deck_id)


def apply_delta(
    col,
    payload: dict,
    *,
    delete_notes_on_removal: bool = False,
    protected_fields: set[str] | None = None,
    protected_tags: set[str] | None = None,
) -> None:
    models_map = _apply_note_types(col, payload["note_types"], allow_structural=False)
    _apply_notes(
        col,
        payload["deck_name"],
        payload["notes"],
        models_map,
        delete_notes_on_removal=delete_notes_on_removal,
        protected_fields=protected_fields or set(),
        protected_tags=protected_tags or set(),
    )
    _apply_subdeck_moves(col, payload["deck_name"], payload["notes"])


def apply_full(
    col,
    payload: dict,
    *,
    delete_notes_on_removal: bool = False,
    protected_fields: set[str] | None = None,
    protected_tags: set[str] | None = None,
) -> None:
    """Ressincronização completa (FR-035): upsert de tudo + remoção do que saiu."""
    models_map = _apply_note_types(col, payload["note_types"], allow_structural=True)
    _apply_notes(
        col,
        payload["deck_name"],
        payload["notes"],
        models_map,
        delete_notes_on_removal=delete_notes_on_removal,
        protected_fields=protected_fields or set(),
        protected_tags=protected_tags or set(),
    )
    _apply_subdeck_moves(col, payload["deck_name"], payload["notes"])

    remote_guids = {n["guid"] for n in payload["notes"]}
    for note_id in col.find_notes(f'deck:"{payload["deck_name"]}"'):
        guid = col.db.scalar("select guid from notes where id = ?", note_id)
        if guid not in remote_guids:
            _remove_or_mark(
                col, note_id, delete_notes_on_removal=delete_notes_on_removal
            )


def perform_sync(
    col, client, deck_id: str, *, delete_notes_on_removal: bool = False
) -> dict:
    """Aplica delta (ou full) e mídia de um deck dentro do run atual."""
    since_mod = state.last_synced_mod(deck_id)
    get_protection = getattr(client, "get_deck_protection", None)
    protection = get_protection(deck_id) if get_protection else {}
    protected_fields = set(protection.get("fields", []))
    protected_tags = set(protection.get("tags", []))
    payload = client.get_deck_delta(deck_id, since_mod)
    if payload.get("full_resync_required"):
        payload = client.get_deck_full(deck_id)
        apply_full(
            col,
            payload,
            delete_notes_on_removal=delete_notes_on_removal,
            protected_fields=protected_fields,
            protected_tags=protected_tags,
        )
    else:
        try:
            apply_delta(
                col,
                payload,
                delete_notes_on_removal=delete_notes_on_removal,
                protected_fields=protected_fields,
                protected_tags=protected_tags,
            )
        except FullResyncRequired:
            payload = client.get_deck_full(deck_id)
            apply_full(
                col,
                payload,
                delete_notes_on_removal=delete_notes_on_removal,
                protected_fields=protected_fields,
                protected_tags=protected_tags,
            )
    media_mod.sync_media(col, payload.get("media", []), client)
    return payload


def sync_decks(col, client, deck_options: list[tuple[str, bool]]) -> list[dict]:
    """Sincroniza todos decks sob um backup e uma transação de estado."""
    if not deck_options:
        return []
    backup_path = backup_mod.create_backup(col)  # FR-033: um snapshot por run
    results = []
    try:
        for deck_id, delete_notes_on_removal in deck_options:
            payload = perform_sync(
                col,
                client,
                deck_id,
                delete_notes_on_removal=delete_notes_on_removal,
            )
            results.append((deck_id, payload))
        with state.database.atomic():
            for deck_id, payload in results:
                state.record_synced_notes(deck_id, payload["notes"])
    except Exception:
        backup_mod.restore_backup(col, backup_path)  # FR-039
        raise
    return [payload for _, payload in results]
