"""Create-only export of one local Anki deck to the first web snapshot."""

import hashlib
from pathlib import Path


class PublishError(RuntimeError):
    pass


def _deck_query(name: str) -> str:
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'deck:"{escaped}"'


def _relative_deck_path(col, note_id, root_name: str) -> str:
    card_ids = col.card_ids_of_note(note_id)
    if not card_ids:
        return ""
    card_deck = col.decks.name(col.get_card(card_ids[0]).did)
    prefix = f"{root_name}::"
    return card_deck[len(prefix) :] if card_deck.startswith(prefix) else ""


def _note_type_payload(notetype: dict) -> dict:
    return {
        "name": notetype["name"],
        "field_names": [field["name"] for field in notetype["flds"]],
        "templates": [
            {"name": t["name"], "qfmt": t["qfmt"], "afmt": t["afmt"]}
            for t in notetype["tmpls"]
        ],
        "css": notetype.get("css", ""),
    }


def collect_media_blobs(
    col, mid: int, field_values: dict, media_dir: Path | None = None
) -> dict[str, tuple[str, bytes]]:
    """Mídia local referenciada nos campos: {sha256: (filename, bytes)}.

    Usado no publish e no envio de sugestões (a mídia nova precisa subir junto,
    senão a nota oficial referencia um arquivo que não existe no servidor).
    """
    if media_dir is None:
        media_dir = Path(col.media.dir()).resolve()
    blobs: dict[str, tuple[str, bytes]] = {}
    for value in field_values.values():
        for filename in col.media.files_in_str(mid, value):
            media_path = (media_dir / filename).resolve()
            if media_dir not in media_path.parents or not media_path.is_file():
                continue
            content = media_path.read_bytes()
            blobs.setdefault(hashlib.sha256(content).hexdigest(), (filename, content))
    return blobs


def build_publish_payload(
    col, deck_id: int, subject_tags: list[str] | None = None
) -> tuple[dict, dict[str, tuple[str, bytes]]]:
    root_name = col.decks.name_if_exists(deck_id)
    if not root_name:
        raise PublishError("O deck selecionado não existe mais.")
    note_ids = list(col.find_notes(_deck_query(root_name)))
    if not note_ids:
        raise PublishError("O deck selecionado não possui notas.")

    notes = [col.get_note(note_id) for note_id in note_ids]
    # um deck pode ter várias notas de tipos distintos: uma entrada em note_types
    # por tipo, na ordem de primeira ocorrência (research.md Decisão 5)
    mid_order: list[int] = []
    for note in notes:
        if note.mid not in mid_order:
            mid_order.append(note.mid)
    mid_index = {mid: i for i, mid in enumerate(mid_order)}

    media_dir = Path(col.media.dir()).resolve()
    media_blobs: dict[str, tuple[str, bytes]] = {}
    exported_notes = []
    for note_id, note in zip(note_ids, notes, strict=True):
        field_values = dict(note.items())
        exported_notes.append(
            {
                "guid": note.guid,
                "field_values": field_values,
                "tags": list(note.tags),
                "anki_deck_path": _relative_deck_path(col, note_id, root_name),
                "note_type_index": mid_index[note.mid],
            }
        )
        for content_hash, blob in collect_media_blobs(
            col, note.mid, field_values, media_dir
        ).items():
            media_blobs.setdefault(content_hash, blob)

    payload = {
        "name": root_name,
        "subject_tags": subject_tags or [],
        "note_types": [_note_type_payload(col.models.get(mid)) for mid in mid_order],
        "notes": exported_notes,
        "media": [
            {"filename": filename, "content_hash": content_hash}
            for content_hash, (filename, _content) in media_blobs.items()
        ],
    }
    return payload, media_blobs


def publish_initial_deck(
    col,
    client,
    local_deck_id: int,
    remote_deck_id: str,
    subject_tags: list[str] | None = None,
) -> dict:
    payload, media_blobs = build_publish_payload(col, local_deck_id, subject_tags)
    return publish_uploads(client, remote_deck_id, payload, media_blobs)


def publish_uploads(client, remote_deck_id: str, payload: dict, media_blobs: dict) -> dict:
    """Fase de rede do publish (US4/T029): sem leitura da coleção.

    Roda numa `QueryOp(...).without_collection()`: o payload já foi montado a
    partir da coleção antes desta fase.
    """
    result = client.publish_deck(remote_deck_id, payload)
    # o backend só devolve URL para hash inédito (get_or_create), então re-upload de
    # mídia já existente já é pulado no servidor. Confirmamos cada upload logo após
    # seu sucesso: um crash no meio deixa os confirmados prontos e o confirm é
    # idempotente na retentativa (FR-004/FR-006, contracts/media-sync.md §4/§5).
    for content_hash, url in result.get("media_upload_urls", {}).items():
        filename, content = media_blobs[content_hash]
        client.upload_signed_media(url, filename, content)
        client.confirm_media_upload(remote_deck_id, content_hash)
    return result
