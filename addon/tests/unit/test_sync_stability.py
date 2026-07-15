"""US4: suíte de estabilidade do sync (FR-014).

Idempotência, convergência após interrupção, casos-limite de conteúdo, fallback
de full-resync, imutabilidade do scheduling (Princípio VIII) e proteção de
campos/tags (Princípio II). Reusa o mesmo formato de payload de test_delta_apply.
"""

import pytest
from anki.collection import Collection

from ankihub_br.db import models as state_db
from ankihub_br.main import sync

NT_ID = "nt-1"


@pytest.fixture
def col(tmp_path):
    collection = Collection(str(tmp_path / "collection.anki2"))
    yield collection
    collection.close()


@pytest.fixture
def state(tmp_path):
    state_db.init_db(tmp_path / "state.sqlite3")
    yield
    state_db.close_db()


def _payload(notes, templates=None, deck_name="Direito Penal"):
    return {
        "deck_name": deck_name,
        "note_types": [
            {
                "id": NT_ID,
                "name": "Básico BR",
                "field_names": ["Frente", "Verso"],
                "templates": templates
                or [{"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"}],
                "css": "",
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


def _guids(col):
    return sorted(r[0] for r in col.db.all("select guid from notes"))


# --- T025: idempotência e interrupção/retomada ---


def test_repeated_delta_no_changes_is_idempotent(col):
    """Reaplicar o mesmo delta não cria/remove/duplica notas nem altera conteúdo."""
    sync.apply_delta(col, _payload([_note("n1"), _note("n2")]))
    before_count = col.db.scalar("select count() from notes")
    before = {g: col.get_note(_nid(col, g)).fields for g in ("n1", "n2")}

    sync.apply_delta(col, _payload([_note("n1"), _note("n2")]))

    assert col.db.scalar("select count() from notes") == before_count
    assert _guids(col) == ["n1", "n2"]  # sem duplicatas
    assert {g: col.get_note(_nid(col, g)).fields for g in ("n1", "n2")} == before


def test_interrupted_then_full_delta_converges_without_orphans(col):
    """Delta parcial (1 nota) seguido do delta completo (2) converge sem órfãos."""
    sync.apply_delta(col, _payload([_note("n1")]))  # primeira passada interrompida
    assert _guids(col) == ["n1"]

    sync.apply_delta(col, _payload([_note("n1"), _note("n2")]))  # retomada completa

    assert _guids(col) == ["n1", "n2"]
    assert col.db.scalar("select count() from notes") == 2  # nenhum guid duplicado


# --- T026: casos-limite de conteúdo e movimento de subdeck ---


def test_content_edge_cases_apply_cleanly(col):
    big = "x" * 100_000
    special = "Ção — “aspas” <b>ok</b> 😀 \t\\ e=mc²"
    sync.apply_delta(
        col,
        _payload(
            [
                _note("empty", frente="", verso=""),
                _note("big", frente=big, verso="v"),
                _note("special", frente=special, verso="π"),
            ]
        ),
    )

    assert col.get_note(_nid(col, "empty")).fields == ["", ""]
    assert col.get_note(_nid(col, "big")).fields[0] == big
    assert col.get_note(_nid(col, "special")).fields == [special, "π"]


def test_subdeck_move_applies_cleanly(col):
    sync.apply_delta(col, _payload([_note("n1", path="Parte Geral")]))
    card = col.get_card(col.card_ids_of_note(_nid(col, "n1"))[0])
    assert col.decks.name(card.did) == "Direito Penal::Parte Geral"

    # move para outro subdeck no delta seguinte
    sync.apply_delta(col, _payload([_note("n1", path="Parte Especial")]))
    card = col.get_card(col.card_ids_of_note(_nid(col, "n1"))[0])
    assert col.decks.name(card.did) == "Direito Penal::Parte Especial"


# --- T027: mudança estrutural do note type dispara full-resync (não apply parcial) ---


class _StructuralClient:
    """Delta estruturalmente irreconciliável; full traz a versão completa."""

    def __init__(self, delta, full):
        self._delta = delta
        self._full = full
        self.calls = []

    def get_deck_delta(self, deck_id, since_mod=None):
        self.calls.append("delta")
        return self._delta

    def get_deck_full(self, deck_id):
        self.calls.append("full")
        return self._full

    def get_media_url(self, content_hash):
        raise AssertionError("sem mídia neste teste")


def test_structural_change_triggers_full_resync_path(col, state):
    sync.apply_delta(col, _payload([_note("n1")]))  # 1 template local
    two_templates = [
        {"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"},
        {"name": "Card 2", "qfmt": "{{Verso}}", "afmt": "{{Frente}}"},
    ]
    client = _StructuralClient(
        delta=_payload([_note("n1")], templates=two_templates),
        full=_payload([_note("n1"), _note("n2")], templates=two_templates),
    )

    sync.perform_sync(col, client, "deck-1")

    assert client.calls == ["delta", "full"]  # caiu no fallback, não apply parcial
    model = col.models.by_name("Básico BR")
    assert len(model["tmpls"]) == 2
    assert _guids(col) == ["n1", "n2"]


# --- T028: Princípio VIII — scheduling byte-idêntico antes/depois de qualquer sync ---


def _card_state(col):
    """Snapshot de todo o scheduling: colunas de `cards` + `revlog` inteiro."""
    cards = col.db.all(
        "select id, type, queue, due, ivl, factor, reps, lapses, left, odue, odid "
        "from cards order by id"
    )
    revlog = col.db.all(
        "select id, cid, ease, ivl, lastIvl, factor, time, type from revlog order by id"
    )
    return cards, revlog


def _review_first_card(col, guid):
    # getCard só serve cards do deck selecionado; a nota vive num subdeck próprio
    card_id = col.card_ids_of_note(_nid(col, guid))[0]
    col.decks.select(col.get_card(card_id).did)
    card = col.sched.getCard()
    assert card is not None
    col.sched.answerCard(card, 3)  # gera revlog + ivl/due não-default


@pytest.mark.parametrize("apply_fn", [sync.apply_delta, sync.apply_full])
def test_sync_never_touches_card_scheduling(col, apply_fn):
    """Aplicar conteúdo (delta ou full) nunca altera ease/interval/due/revlog."""
    sync.apply_delta(col, _payload([_note("n1", frente="original")]))
    _review_first_card(col, "n1")
    before = _card_state(col)

    apply_fn(col, _payload([_note("n1", frente="conteúdo corrigido")]))

    assert _card_state(col) == before  # byte-idêntico


# --- T029: edição remota em campo/tag protegido não toca o valor local (Princípio II) ---


def test_remote_edit_leaves_protected_field_and_tag_untouched(col):
    sync.apply_delta(col, _payload([_note("n1", frente="oficial", verso="oficial")]))
    note = col.get_note(_nid(col, "n1"))
    note.fields = ["meu valor", "oficial"]
    note.tags = ["penal", "pessoal"]
    col.update_note(note)

    sync.apply_delta(
        col,
        _payload([_note("n1", frente="NOVO oficial", verso="verso novo", tags=["penal"])]),
        protected_fields={"Frente"},
        protected_tags={"pessoal"},
    )

    updated = col.get_note(_nid(col, "n1"))
    assert updated.fields[0] == "meu valor"  # campo protegido intacto
    assert updated.fields[1] == "verso novo"  # campo não protegido atualiza
    assert "pessoal" in updated.tags  # tag protegida preservada
