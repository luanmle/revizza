import hashlib
from pathlib import Path

import pytest
from anki.collection import Collection

from ankihub_br.main import publish


@pytest.fixture
def col(tmp_path):
    collection = Collection(str(tmp_path / "collection.anki2"))
    yield collection
    collection.close()


def test_builds_create_only_payload_with_subdeck_and_media(col):
    root_id = col.decks.id("Direito")
    subdeck_id = col.decks.id("Direito::Penal")
    media = b"fake-png"
    Path(col.media.dir(), "figura.png").write_bytes(media)
    note = col.new_note(col.models.current())
    note.fields = ['<img src="figura.png">', "Resposta"]
    note.tags = ["penal"]
    col.add_note(note, subdeck_id)

    payload, blobs = publish.build_publish_payload(col, root_id, ["Direito"])

    digest = hashlib.sha256(media).hexdigest()
    assert payload["name"] == "Direito"
    assert payload["subject_tags"] == ["Direito"]
    assert payload["notes"][0]["anki_deck_path"] == "Penal"
    assert payload["notes"][0]["field_values"]["Front"].startswith("<img")
    assert payload["media"] == [{"filename": "figura.png", "content_hash": digest}]
    assert blobs[digest] == ("figura.png", media)


def test_publishes_snapshot_then_uploads_only_requested_media(col):
    deck_id = col.decks.id("Direito")
    note = col.new_note(col.models.current())
    note.fields = ["Pergunta", "Resposta"]
    col.add_note(note, deck_id)

    class Client:
        def __init__(self):
            self.calls = []

        def publish_deck(self, remote_id, payload):
            self.calls.append(("publish", remote_id, payload["notes"][0]["guid"]))
            return {"note_count": 1, "media_upload_urls": {}}

        def upload_signed_media(self, *_args):
            raise AssertionError("não há mídia para enviar")

    client = Client()
    result = publish.publish_initial_deck(col, client, deck_id, "remote-id")

    assert result["note_count"] == 1
    assert client.calls[0][:2] == ("publish", "remote-id")


def test_accepts_deck_with_multiple_note_types(col):
    deck_id = col.decks.id("Direito")
    first = col.new_note(col.models.current())
    first.fields = ["A", "B"]
    col.add_note(first, deck_id)

    alternate = col.models.new("Alternativo")
    col.models.add_field(alternate, col.models.new_field("Texto"))
    template = col.models.new_template("Card 1")
    template["qfmt"] = "{{Texto}}"
    template["afmt"] = "{{Texto}}"
    col.models.add_template(alternate, template)
    col.models.add(alternate)
    second = col.new_note(alternate)
    second.fields = ["C"]
    col.add_note(second, deck_id)

    payload, _blobs = publish.build_publish_payload(col, deck_id)

    names = [nt["name"] for nt in payload["note_types"]]
    assert names == ["Basic", "Alternativo"]  # ordem de primeira ocorrência
    # cada nota aponta para o índice do seu próprio tipo
    by_guid = {n["guid"]: n["note_type_index"] for n in payload["notes"]}
    assert by_guid[first.guid] == 0
    assert by_guid[second.guid] == 1
