"""Contract: note detail rewrites <img src> to signed Storage URLs (web render)."""

import pytest

from apps.notes.models import MediaFile

pytestmark = pytest.mark.django_db

HASH = "b" * 64


@pytest.fixture(autouse=True)
def _stub_sign(monkeypatch):
    monkeypatch.setattr(
        "apps.notes.serializers.media.signed_download_url",
        lambda path: f"https://storage.example/{path}?signed",
    )


def test_note_detail_rewrites_img_src_to_signed_url(api_client, make_note):
    note = make_note(
        field_values={"Frente": 'Veja <img src="lion.jpg"> aqui', "Verso": "sem mídia"}
    )
    MediaFile.objects.create(
        deck=note.deck,
        content_hash=HASH,
        storage_path=f"{note.deck_id}/{HASH}",
        original_filename="lion.jpg",
        status="ready",
    )

    body = api_client.get(f"/api/v1/notes/{note.id}/").json()

    src = f'src="https://storage.example/{note.deck_id}/{HASH}?signed"'
    assert body["field_values"]["Frente"] == f"Veja <img {src}> aqui"
    assert body["field_values"]["Verso"] == "sem mídia"  # campo sem mídia intacto


def test_unresolved_or_pending_media_leaves_src_untouched(api_client, make_note):
    note = make_note(field_values={"Frente": '<img src="faltando.png">'})
    MediaFile.objects.create(
        deck=note.deck,
        content_hash=HASH,
        storage_path=f"{note.deck_id}/{HASH}",
        original_filename="pendente.png",
        status="pending_upload",  # ainda não pronta → não reescreve
    )

    body = api_client.get(f"/api/v1/notes/{note.id}/").json()

    assert body["field_values"]["Frente"] == '<img src="faltando.png">'
