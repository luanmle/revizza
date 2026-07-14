"""Protection checks while applying web→Anki deltas (FR-040 to FR-044)."""

import pytest
from anki.collection import Collection

from ankihub_br.main import sync

NT_ID = "nt-1"


@pytest.fixture
def col(tmp_path):
    collection = Collection(str(tmp_path / "collection.anki2"))
    yield collection
    collection.close()


def _payload(front="Oficial", back="Resposta", tags=None, back_name="Verso"):
    return {
        "deck_name": "Direito",
        "note_types": [
            {
                "id": NT_ID,
                "name": "Básico BR",
                "field_names": ["Frente", back_name],
                "templates": [
                    {
                        "name": "Card 1",
                        "qfmt": "{{Frente}}",
                        "afmt": "{{%s}}" % back_name,
                    }
                ],
                "css": "",
            }
        ],
        "notes": [
            {
                "guid": "n1",
                "note_type_id": NT_ID,
                "field_values": {"Frente": front, back_name: back},
                "tags": tags or ["oficial"],
                "anki_deck_path": "",
                "mod": "2026-07-13T00:00:00+00:00",
                "deleted": False,
            }
        ],
        "subdecks": [],
        "media": [],
    }


def _note(col):
    note_id = col.db.scalar("select id from notes where guid = ?", "n1")
    return col.get_note(note_id)


def test_configured_fields_tags_and_internal_tags_are_preserved(col):
    sync.apply_delta(col, _payload())
    note = _note(col)
    note.fields = ["Minha frente", "Meu verso"]
    note.tags = ["pessoal", "descartavel", "leech", "marked"]
    col.update_note(note)

    sync.apply_delta(
        col,
        _payload(front="Frente nova", back="Verso novo", tags=["oficial-nova"]),
        protected_fields={"Frente"},
        protected_tags={"pessoal"},
    )

    updated = _note(col)
    assert updated.fields == ["Minha frente", "Verso novo"]
    assert set(updated.tags) == {"oficial-nova", "pessoal", "leech", "marked"}


def test_per_note_protection_tag_preserves_named_field(col):
    sync.apply_delta(col, _payload())
    note = _note(col)
    note.fields[1] = "Verso pessoal"
    note.tags.append("AnkiHubBR_Protect::Verso")
    col.update_note(note)

    sync.apply_delta(col, _payload(back="Verso oficial novo"))

    updated = _note(col)
    assert updated.fields[1] == "Verso pessoal"
    assert "AnkiHubBR_Protect::Verso" in updated.tags


def test_per_note_protection_tag_decodes_multi_word_field(col):
    field_name = "Notas pessoais"
    sync.apply_delta(col, _payload(back_name=field_name))
    note = _note(col)
    note.fields[1] = "Conteúdo pessoal"
    note.tags.append("AnkiHubBR_Protect::Notas_pessoais")
    col.update_note(note)

    sync.apply_delta(col, _payload(back="Conteúdo oficial novo", back_name=field_name))

    updated = _note(col)
    assert updated.fields[1] == "Conteúdo pessoal"
