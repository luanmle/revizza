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
    notetype_ids = {note.mid for note in notes}
    if len(notetype_ids) != 1:
        raise PublishError(
            "A importação inicial aceita um único tipo de nota por deck."
        )
    notetype = notes[0].note_type()
    if not notetype:
        raise PublishError("Não foi possível ler o tipo de nota do deck.")

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
            }
        )
        for value in field_values.values():
            for filename in col.media.files_in_str(note.mid, value):
                media_path = (media_dir / filename).resolve()
                if media_dir not in media_path.parents or not media_path.is_file():
                    continue
                content = media_path.read_bytes()
                content_hash = hashlib.sha256(content).hexdigest()
                media_blobs.setdefault(content_hash, (filename, content))

    payload = {
        "name": root_name,
        "subject_tags": subject_tags or [],
        "note_type": {
            "name": notetype["name"],
            "field_names": [field["name"] for field in notetype["flds"]],
            "templates": [
                {
                    "name": template["name"],
                    "qfmt": template["qfmt"],
                    "afmt": template["afmt"],
                }
                for template in notetype["tmpls"]
            ],
            "css": notetype.get("css", ""),
        },
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
    result = client.publish_deck(remote_deck_id, payload)
    for content_hash, url in result.get("media_upload_urls", {}).items():
        filename, content = media_blobs[content_hash]
        client.upload_signed_media(url, filename, content)
    return result
