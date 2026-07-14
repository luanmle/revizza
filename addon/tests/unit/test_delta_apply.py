"""T033: aplicação do delta na ordem tipos de nota → notas → subdecks (FR-034)."""

import pytest
from anki.collection import Collection

from ankihub_br.main import sync

NT_ID = "nt-1"


@pytest.fixture
def col(tmp_path):
    collection = Collection(str(tmp_path / "collection.anki2"))
    yield collection
    collection.close()


def _payload(notes, templates=None):
    return {
        "deck_name": "Direito Penal",
        "note_types": [
            {
                "id": NT_ID,
                "name": "Básico BR",
                "field_names": ["Frente", "Verso"],
                "templates": templates
                or [{"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"}],
                "css": ".card { color: black; }",
            }
        ],
        "notes": notes,
        "subdecks": sorted(
            {n.get("anki_deck_path") for n in notes if n.get("anki_deck_path")}
        ),
        "media": [],
    }


def _note(guid, frente="Q", verso="A", path="", deleted=False, tags=None):
    return {
        "guid": guid,
        "note_type_id": NT_ID,
        "field_values": {"Frente": frente, "Verso": verso},
        "tags": tags if tags is not None else ["penal"],
        "anki_deck_path": path,
        "mod": "2026-07-13T00:00:00+00:00",
        "deleted": deleted,
    }


def _nid(col, guid):
    return col.db.scalar("select id from notes where guid = ?", guid)


def test_delta_creates_notetype_notes_and_subdecks(col):
    sync.apply_delta(col, _payload([_note("n1", path="Parte Geral"), _note("n2")]))

    model = col.models.by_name("Básico BR")
    assert [f["name"] for f in model["flds"]] == ["Frente", "Verso"]
    assert model["tmpls"][0]["qfmt"] == "{{Frente}}"
    assert model["css"] == ".card { color: black; }"

    note = col.get_note(_nid(col, "n1"))
    assert note.fields == ["Q", "A"]
    assert note.tags == ["penal"]

    card = col.get_card(col.card_ids_of_note(_nid(col, "n1"))[0])
    assert col.decks.name(card.did) == "Direito Penal::Parte Geral"
    card2 = col.get_card(col.card_ids_of_note(_nid(col, "n2"))[0])
    assert col.decks.name(card2.did) == "Direito Penal"


def test_delta_creates_multiple_note_types_and_maps_each_note(col):
    """US2: payload com 2 tipos recria ambos e associa cada nota pelo note_type_id."""
    payload = {
        "deck_name": "Direito Penal",
        "note_types": [
            {
                "id": "nt-basica",
                "name": "Básico BR",
                "field_names": ["Frente", "Verso"],
                "templates": [{"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"}],
                "css": "",
            },
            {
                "id": "nt-cloze",
                "name": "Cloze BR",
                "field_names": ["Texto", "Extra"],
                "templates": [{"name": "Cloze", "qfmt": "{{cloze:Texto}}", "afmt": "{{cloze:Texto}}"}],
                "css": "",
            },
        ],
        "notes": [
            {"guid": "b1", "note_type_id": "nt-basica", "field_values": {"Frente": "Q", "Verso": "A"},
             "tags": [], "anki_deck_path": "", "mod": "2026-07-13T00:00:00+00:00", "deleted": False},
            {"guid": "c1", "note_type_id": "nt-cloze", "field_values": {"Texto": "{{c1::x}}", "Extra": "E"},
             "tags": [], "anki_deck_path": "", "mod": "2026-07-13T00:00:00+00:00", "deleted": False},
        ],
        "subdecks": [],
        "media": [],
    }

    sync.apply_delta(col, payload)

    assert col.models.by_name("Básico BR") is not None
    assert col.models.by_name("Cloze BR") is not None
    basica = col.get_note(_nid(col, "b1"))
    cloze = col.get_note(_nid(col, "c1"))
    assert basica.note_type()["name"] == "Básico BR"
    assert cloze.note_type()["name"] == "Cloze BR"
    assert cloze.fields == ["{{c1::x}}", "E"]


def test_delta_updates_existing_note_by_guid(col):
    sync.apply_delta(col, _payload([_note("n1")]))

    sync.apply_delta(
        col, _payload([_note("n1", frente="Q corrigida", tags=["penal", "revisado"])])
    )

    note = col.get_note(_nid(col, "n1"))
    assert note.fields[0] == "Q corrigida"
    assert note.tags == ["penal", "revisado"]
    assert col.db.scalar("select count() from notes") == 1


def test_deletion_marks_note_by_default_preserving_history(col):
    sync.apply_delta(col, _payload([_note("n1")]))

    sync.apply_delta(col, _payload([_note("n1", deleted=True)]))

    note = col.get_note(_nid(col, "n1"))  # FR-037: nota preservada, só marcada
    assert sync.REMOVED_TAG in note.tags


def test_deletion_removes_note_when_pref_set(col):
    sync.apply_delta(col, _payload([_note("n1")]))

    sync.apply_delta(
        col, _payload([_note("n1", deleted=True)]), delete_notes_on_removal=True
    )

    assert _nid(col, "n1") is None


def test_structural_template_change_raises_full_resync(col):
    sync.apply_delta(col, _payload([_note("n1")]))
    two_templates = [
        {"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"},
        {"name": "Card 2", "qfmt": "{{Verso}}", "afmt": "{{Frente}}"},
    ]

    with pytest.raises(sync.FullResyncRequired):  # FR-035
        sync.apply_delta(col, _payload([_note("n1")], templates=two_templates))


def test_apply_full_reconciles_structure_and_removes_stale_notes(col):
    sync.apply_delta(col, _payload([_note("n1"), _note("n2")]))
    two_templates = [
        {"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"},
        {"name": "Card 2", "qfmt": "{{Verso}}", "afmt": "{{Frente}}"},
    ]

    sync.apply_full(
        col,
        _payload([_note("n1")], templates=two_templates),
        delete_notes_on_removal=True,
    )

    model = col.models.by_name("Básico BR")
    assert len(model["tmpls"]) == 2
    assert _nid(col, "n1") is not None
    assert _nid(col, "n2") is None  # saiu da base oficial
