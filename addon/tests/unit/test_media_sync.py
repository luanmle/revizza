"""011 Fase 2: mídia por hash + imutabilidade de agendamento (Princípio VIII).

T016 cobre SC-007: um apply_delta/apply_full com mídia reescreve só o <img src>
da nota (FR-011) e NÃO toca em nenhum campo de agendamento do card.
"""

import hashlib
import os
import time

import pytest
from anki.collection import Collection

from ankihub_br.ankihub_br_client.client import (
    MEDIA_MAX_BYTES,
    AnkiHubBrClient,
    MediaTooLarge,
)
from ankihub_br.db import models as state_db
from ankihub_br.main import media as media_mod
from ankihub_br.main import sync

NT_ID = "nt-1"
HASH = "a" * 64
RESOLVED = f"{HASH}.png"


@pytest.fixture
def col(tmp_path):
    collection = Collection(str(tmp_path / "collection.anki2"))
    yield collection
    collection.close()


def _payload(notes, media=None):
    return {
        "deck_name": "Direito Penal",
        "note_types": [
            {
                "id": NT_ID,
                "name": "Básico BR",
                "field_names": ["Frente", "Verso"],
                "templates": [
                    {"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"}
                ],
                "css": "",
            }
        ],
        "notes": notes,
        "subdecks": [],
        "media": media or [],
    }


def _note(guid, frente, verso="A", tags=None):
    return {
        "guid": guid,
        "note_type_id": NT_ID,
        "field_values": {"Frente": frente, "Verso": verso},
        "tags": tags if tags is not None else ["penal"],
        "anki_deck_path": "",
        "mod": "2026-07-13T00:00:00+00:00",
        "deleted": False,
    }


def _nid(col, guid):
    return col.db.scalar("select id from notes where guid = ?", guid)


def _sched_snapshot(col, guid):
    card = col.get_card(col.card_ids_of_note(_nid(col, guid))[0])
    return (card.due, card.ivl, card.factor, card.reps, card.queue, card.type)


MEDIA_MAP = {"figura.png": RESOLVED}


def test_media_map_rewrites_only_img_src_on_create(col):
    frente = 'Pergunta <img src="figura.png"> fim'
    sync.apply_delta(col, _payload([_note("n1", frente)]), media_map=MEDIA_MAP)

    note = col.get_note(_nid(col, "n1"))
    assert note.fields[0] == f'Pergunta <img src="{RESOLVED}"> fim'
    assert note.fields[1] == "A"  # campo sem mídia intacto


def test_scheduling_untouched_by_media_bearing_delta(col):
    """Princípio VIII / SC-007: due/ivl/factor/reps/queue byte-idênticos."""
    frente = '<img src="figura.png">'
    sync.apply_delta(col, _payload([_note("n1", frente)]), media_map=MEDIA_MAP)

    # simula que o assinante estudou o card (estado de agendamento não-default)
    cid = col.card_ids_of_note(_nid(col, "n1"))[0]
    card = col.get_card(cid)
    card.due, card.ivl, card.factor, card.reps, card.queue, card.type = (
        999,
        42,
        2500,
        7,
        2,
        2,
    )
    col.update_card(card)
    before = _sched_snapshot(col, "n1")

    # nova sincronização com mídia (mesmo hash, download já não é necessário)
    sync.apply_delta(
        col,
        _payload([_note("n1", frente, verso="Resposta nova")]),
        media_map=MEDIA_MAP,
    )

    assert _sched_snapshot(col, "n1") == before  # agendamento imutável
    note = col.get_note(_nid(col, "n1"))
    assert note.fields[1] == "Resposta nova"  # conteúdo atualizou
    assert note.fields[0] == f'<img src="{RESOLVED}">'


def test_full_state_unchanged_except_img_src(col):
    """Todo valor de campo/tag além do <img src> permanece idêntico."""
    frente = 'A <img src="figura.png"> B'
    payload = _payload([_note("n1", frente, verso="Verso", tags=["t1", "t2"])])
    sync.apply_full(col, payload, media_map=MEDIA_MAP)

    note = col.get_note(_nid(col, "n1"))
    assert note.fields == [f'A <img src="{RESOLVED}"> B', "Verso"]
    assert sorted(note.tags) == ["t1", "t2"]


def test_unresolved_hash_leaves_reference_untouched(col):
    """F1: hash ausente do media_map mantém o <img src> original (nota commita)."""
    frente = '<img src="figura.png">'
    sync.apply_delta(col, _payload([_note("n1", frente)]), media_map={})

    note = col.get_note(_nid(col, "n1"))
    assert note.fields[0] == '<img src="figura.png">'  # intacto


class _FakeClient:
    """Client mínimo: get_media_url + download_file por hash."""

    def __init__(self, blobs: dict[str, bytes]):
        self.blobs = blobs
        self.download_calls: list[str] = []

    def get_media_url(self, content_hash: str) -> str:
        return f"https://storage/{content_hash}"

    def download_file(self, url: str) -> bytes:
        content_hash = url.rsplit("/", 1)[1]
        self.download_calls.append(content_hash)
        return self.blobs[content_hash]


def test_stage_and_commit_round_trip(col, tmp_path):
    data = b"\x89PNG fake bytes"
    good_hash = hashlib.sha256(data).hexdigest()
    client = _FakeClient({good_hash: data})
    items = [{"filename": "figura.png", "content_hash": good_hash}]

    staged = media_mod.stage_media(col, items, client, tmp_path)
    resolved = media_mod.commit_media(col, staged)

    assert resolved == {good_hash: f"{good_hash}.png"}
    assert col.media.have(f"{good_hash}.png")

    # segunda passada: já commitado → zero downloads (SC-004)
    client.download_calls.clear()
    media_mod.commit_media(col, media_mod.stage_media(col, items, client, tmp_path))
    assert client.download_calls == []


def test_stage_rejects_hash_mismatch(col, tmp_path):
    manifest_hash = "e" * 64  # não bate com os bytes servidos
    client = _FakeClient({manifest_hash: b"tampered content"})
    items = [{"filename": "x.png", "content_hash": manifest_hash}]

    staged = media_mod.stage_media(col, items, client, tmp_path)

    assert staged == []  # item descartado, ausente do mapa (F1)
    assert media_mod.commit_media(col, staged) == {}
    assert not col.media.have(f"{manifest_hash}.png")


# --- US1 (T017-T019): sincronização de nota com imagem para um perfil novo ---


@pytest.fixture
def state(tmp_path):
    state_db.init_db(tmp_path / "state.sqlite3")
    yield
    state_db.close_db()


def _img_note(guid, filename, verso="A"):
    return _note(guid, f'<img src="{filename}">', verso=verso)


class _FakeSyncClient:
    """Client de sync completo para exercitar perform_sync com mídia."""

    def __init__(self, blobs: dict[str, bytes]):
        self.blobs = blobs
        self.download_calls: list[str] = []
        self.delta: dict = {}

    def get_deck_protection(self, deck_id: str) -> dict:
        return {}

    def get_deck_delta(self, deck_id: str, since_mod=None) -> dict:
        return self.delta

    def get_deck_full(self, deck_id: str) -> dict:
        return self.delta

    def get_media_url(self, content_hash: str) -> str:
        return f"https://storage/{content_hash}"

    def download_file(self, url: str) -> bytes:
        content_hash = url.rsplit("/", 1)[1]
        self.download_calls.append(content_hash)
        return self.blobs[content_hash]


def _media_item(filename, data):
    return {"filename": filename, "content_hash": hashlib.sha256(data).hexdigest()}


def test_image_bearing_note_syncs_to_fresh_profile(col, state):
    """T017: primeira sync instala <hash>.<ext> e a nota o referencia."""
    data = b"PNG-A"
    item = _media_item("figura.png", data)
    client = _FakeSyncClient({item["content_hash"]: data})
    client.delta = _payload(
        [_img_note("n1", "figura.png")], media=[item]
    ) | {"full_resync_required": False}

    sync.perform_sync(col, client, "deck-1")

    resolved = f"{item['content_hash']}.png"
    assert col.media.have(resolved)
    note = col.get_note(_nid(col, "n1"))
    assert note.fields[0] == f'<img src="{resolved}">'


def test_delta_downloads_only_new_media(col, state):
    """T018: delta que acrescenta imagem baixa só a nova; a antiga fica intacta."""
    data_a = b"PNG-A"
    item_a = _media_item("a.png", data_a)
    data_b = b"PNG-B"
    item_b = _media_item("b.png", data_b)
    client = _FakeSyncClient(
        {item_a["content_hash"]: data_a, item_b["content_hash"]: data_b}
    )

    client.delta = _payload([_img_note("n1", "a.png")], media=[item_a]) | {
        "full_resync_required": False
    }
    sync.perform_sync(col, client, "deck-1")
    resolved_a = f"{item_a['content_hash']}.png"
    assert col.media.have(resolved_a)

    client.download_calls.clear()
    # segundo delta lista as duas mídias, mas a antiga já está commitada
    client.delta = _payload(
        [_img_note("n1", "a.png"), _img_note("n2", "b.png")],
        media=[item_a, item_b],
    ) | {"full_resync_required": False}
    sync.perform_sync(col, client, "deck-1")

    assert client.download_calls == [item_b["content_hash"]]  # só a nova
    assert col.media.have(f"{item_b['content_hash']}.png")


def test_content_present_locally_is_reused_without_download(col, state):
    """T019/SC-004: conteúdo já local (via outro deck) não é rebaixado."""
    data = b"PNG-SHARED"
    item = _media_item("shared.png", data)
    resolved = f"{item['content_hash']}.png"
    col.media.write_data(resolved, data)  # simula chegada por outro deck

    client = _FakeSyncClient({item["content_hash"]: data})
    client.delta = _payload([_img_note("n1", "shared.png")], media=[item]) | {
        "full_resync_required": False
    }
    sync.perform_sync(col, client, "deck-1")

    assert client.download_calls == []  # zero downloads para hash já presente
    note = col.get_note(_nid(col, "n1"))
    assert note.fields[0] == f'<img src="{resolved}">'


# --- US2 (T021-T022): mesmo nome + conteúdo diferente não se sobrescrevem ---


def test_same_named_different_content_do_not_clobber(col, state):
    """T021: dois decks com figura.png distintas viram dois arquivos locais."""
    data_a = b"PNG-DECK-A"
    item_a = _media_item("figura.png", data_a)  # mesmo nome de origem
    data_b = b"PNG-DECK-B"
    item_b = _media_item("figura.png", data_b)  # conteúdo diferente → hash diferente
    client = _FakeSyncClient(
        {item_a["content_hash"]: data_a, item_b["content_hash"]: data_b}
    )

    client.delta = _payload([_img_note("n1", "figura.png")], media=[item_a]) | {
        "full_resync_required": False
    }
    sync.perform_sync(col, client, "deck-1")

    client.delta = _payload([_img_note("n2", "figura.png")], media=[item_b]) | {
        "full_resync_required": False
    }
    sync.perform_sync(col, client, "deck-2")

    resolved_a = f"{item_a['content_hash']}.png"
    resolved_b = f"{item_b['content_hash']}.png"
    assert resolved_a != resolved_b  # nomes distintos por conteúdo distinto
    assert col.media.have(resolved_a)
    assert col.media.have(resolved_b)
    assert col.get_note(_nid(col, "n1")).fields[0] == f'<img src="{resolved_a}">'
    assert col.get_note(_nid(col, "n2")).fields[0] == f'<img src="{resolved_b}">'


def test_recolliding_resync_reuses_names_without_churn(col, state):
    """T022/SC-004: re-sync dos dois decks não renomeia nem rebaixa mídia."""
    data_a = b"PNG-DECK-A"
    item_a = _media_item("figura.png", data_a)
    data_b = b"PNG-DECK-B"
    item_b = _media_item("figura.png", data_b)
    client = _FakeSyncClient(
        {item_a["content_hash"]: data_a, item_b["content_hash"]: data_b}
    )
    delta_1 = _payload([_img_note("n1", "figura.png")], media=[item_a]) | {
        "full_resync_required": False
    }
    delta_2 = _payload([_img_note("n2", "figura.png")], media=[item_b]) | {
        "full_resync_required": False
    }
    client.delta = delta_1
    sync.perform_sync(col, client, "deck-1")
    client.delta = delta_2
    sync.perform_sync(col, client, "deck-2")

    resolved_a = f"{item_a['content_hash']}.png"
    resolved_b = f"{item_b['content_hash']}.png"

    client.download_calls.clear()
    client.delta = delta_1
    sync.perform_sync(col, client, "deck-1")
    client.delta = delta_2
    sync.perform_sync(col, client, "deck-2")

    assert client.download_calls == []  # ambos já commitados → zero download
    assert col.media.have(resolved_a)
    assert col.media.have(resolved_b)
    # nomes hash-derivados estáveis: sem churn de renomeação
    assert col.get_note(_nid(col, "n1")).fields[0] == f'<img src="{resolved_a}">'
    assert col.get_note(_nid(col, "n2")).fields[0] == f'<img src="{resolved_b}">'


# --- US3 (T023-T027): mídia inválida/incompleta rejeitada sem corromper nada ---


def _media_files(col) -> list[str]:
    return os.listdir(col.media.dir())


class _FakeHTTPResponse:
    """Resposta stream fake para exercitar AnkiHubBrClient.download_file."""

    def __init__(self, chunks, headers=None):
        self._chunks = chunks
        self.headers = headers or {}
        self.consumed = 0

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=0):
        for chunk in self._chunks:
            self.consumed += 1
            yield chunk

    def close(self):
        pass


def _client_with_response(monkeypatch, response):
    client = AnkiHubBrClient("https://api.example.com")
    monkeypatch.setattr(client.session, "get", lambda *a, **k: response)
    return client


def test_hash_mismatch_discarded_and_collection_unchanged(col, tmp_path):
    """T023/T027: bytes não batem com o manifesto → descartado, nada escrito."""
    manifest_hash = "e" * 64
    client = _FakeClient({manifest_hash: b"tampered content"})
    items = [{"filename": "x.png", "content_hash": manifest_hash}]
    before = _media_files(col)

    staged = media_mod.stage_media(col, items, client, tmp_path)

    assert staged == []  # item reportado como falho (ausente do mapa)
    assert media_mod.commit_media(col, staged) == {}
    assert not col.media.have(f"{manifest_hash}.png")
    assert _media_files(col) == before  # pasta de mídia intacta (T027)


def test_oversized_via_content_length_aborts_before_buffering(monkeypatch):
    """T024: Content-Length acima do limite aborta sem iterar o corpo."""
    response = _FakeHTTPResponse(
        chunks=[b"x"], headers={"Content-Length": str(MEDIA_MAX_BYTES + 1)}
    )
    client = _client_with_response(monkeypatch, response)

    with pytest.raises(MediaTooLarge):
        client.download_file("https://storage/big")
    assert response.consumed == 0  # nunca bufferizou o corpo


def test_oversized_via_streamed_count_aborts_before_full_buffering(monkeypatch):
    """T024: sem/mentindo Content-Length, contagem corrente aborta no meio."""
    chunk = b"x" * (64 * 1024)
    total_chunks = (MEDIA_MAX_BYTES // len(chunk)) + 5  # ultrapassa o limite
    response = _FakeHTTPResponse(chunks=[chunk] * total_chunks, headers={})
    client = _client_with_response(monkeypatch, response)

    with pytest.raises(MediaTooLarge):
        client.download_file("https://storage/big")
    assert response.consumed < total_chunks  # abortou antes de ler tudo


def test_oversized_media_item_omitted_from_map(col, tmp_path):
    """T024: stage_media trata MediaTooLarge omitindo o item (F1)."""

    class _OversizedClient:
        def get_media_url(self, content_hash):
            return f"https://storage/{content_hash}"

        def download_file(self, url):
            raise MediaTooLarge("grande demais")

    items = [{"filename": "big.png", "content_hash": "b" * 64}]
    before = _media_files(col)

    staged = media_mod.stage_media(col, items, _OversizedClient(), tmp_path)

    assert staged == []
    assert _media_files(col) == before


def test_truncated_stream_never_reachable_under_final_name(col, tmp_path):
    """T025: download truncado → hash não bate → nenhum arquivo sob nome final."""
    full_data = b"PNG-completo-com-muitos-bytes"
    manifest_hash = hashlib.sha256(full_data).hexdigest()
    truncated = full_data[:5]  # stream interrompido: bytes parciais
    client = _FakeClient({manifest_hash: truncated})
    items = [{"filename": "t.png", "content_hash": manifest_hash}]
    before = _media_files(col)

    staged = media_mod.stage_media(col, items, client, tmp_path)

    assert staged == []  # validação de hash falhou
    assert not col.media.have(f"{manifest_hash}.png")
    assert not (tmp_path / f"{manifest_hash}.png").exists()  # nem no staging final
    assert _media_files(col) == before


def test_traversal_filename_never_used_as_path(col, tmp_path):
    """T026: nome com ../ nunca vira caminho; escrita só via write_data."""
    data = b"legit content"
    content_hash = hashlib.sha256(data).hexdigest()
    client = _FakeClient({content_hash: data})
    items = [{"filename": "../../../etc/evil.png", "content_hash": content_hash}]

    staged = media_mod.stage_media(col, items, client, tmp_path)
    resolved_map = media_mod.commit_media(col, staged)

    safe_name = f"{content_hash}.png"  # derivado do hash, ../ descartado
    assert resolved_map == {content_hash: safe_name}
    assert col.media.have(safe_name)
    # o único arquivo escrito é o nome seguro dentro da pasta de mídia
    assert _media_files(col) == [safe_name]


# --- US4 (T030/T032): concorrência e cancelamento no staging ---


def test_stage_parallel_downloads_all_items(col, tmp_path):
    """T030: com concurrency>1 todos os itens ainda baixam e validam."""
    blobs = {hashlib.sha256(f"img-{i}".encode()).hexdigest(): f"img-{i}".encode()
             for i in range(6)}
    client = _FakeClient(blobs)
    items = [{"filename": f"{h}.png", "content_hash": h} for h in blobs]

    staged = media_mod.stage_media(col, items, client, tmp_path, concurrency=4)

    assert sorted(s.content_hash for s in staged) == sorted(blobs)
    assert sorted(client.download_calls) == sorted(blobs)


def test_stage_cancellation_stops_new_downloads(col, tmp_path):
    """T032: should_cancel para de submeter downloads; sem .part órfão do cancelado."""
    blobs = {hashlib.sha256(f"c-{i}".encode()).hexdigest(): f"c-{i}".encode()
             for i in range(5)}
    client = _FakeClient(blobs)
    items = [{"filename": f"{h}.png", "content_hash": h} for h in blobs]

    staged = media_mod.stage_media(
        col, items, client, tmp_path, concurrency=1, should_cancel=lambda: True
    )

    assert staged == []  # nada foi submetido
    assert client.download_calls == []
    assert list(tmp_path.glob(".*.part")) == []  # nenhum temp em voo deixado


def test_stage_reports_progress(col, tmp_path):
    """T031: on_progress recebe (processados, total) até completar."""
    data = b"progress-bytes"
    h = hashlib.sha256(data).hexdigest()
    client = _FakeClient({h: data})
    items = [{"filename": "p.png", "content_hash": h}]
    calls: list[tuple[int, int]] = []

    media_mod.stage_media(
        col, items, client, tmp_path, on_progress=lambda d, t: calls.append((d, t))
    )

    assert calls[-1] == (1, 1)


# --- US5 (T034-T036): sync interrompida pode ser retomada com segurança ---


def test_partial_media_failure_commits_all_notes_and_advances_cursor(col, state):
    """T034: uma mídia falha; ambas notas commitam, cursor avança, <img> falho intacto."""
    good = b"PNG-bom"
    item_good = _media_item("bom.png", good)
    item_bad = _media_item("ruim.png", b"ORIGINAL")  # hash do manifesto
    # o client só conhece a boa; a ruim levanta KeyError no download (falha F1)
    client = _FakeSyncClient({item_good["content_hash"]: good})
    client.delta = _payload(
        [_img_note("n1", "bom.png"), _img_note("n2", "ruim.png")],
        media=[item_good, item_bad],
    ) | {"full_resync_required": False}

    sync.sync_decks(col, client, [("deck-1", False)])

    resolved_good = f"{item_good['content_hash']}.png"
    assert col.get_note(_nid(col, "n1")).fields[0] == f'<img src="{resolved_good}">'
    assert col.get_note(_nid(col, "n2")).fields[0] == '<img src="ruim.png">'  # intacto
    # cursor avança normalmente: a nota commitou (research.md §9)
    assert state_db.last_synced_mod("deck-1") == "2026-07-13T00:00:00+00:00"


def test_retry_after_partial_failure_only_redownloads_missing(col, state):
    """T035: retentativa não rebaixa a mídia já commitada; só a que faltava (SC-004)."""
    good = b"PNG-bom"
    item_good = _media_item("bom.png", good)
    item_bad = _media_item("ruim.png", b"ORIGINAL")
    client = _FakeSyncClient({item_good["content_hash"]: good})
    client.delta = _payload(
        [_img_note("n1", "bom.png"), _img_note("n2", "ruim.png")],
        media=[item_good, item_bad],
    ) | {"full_resync_required": False}
    sync.sync_decks(col, client, [("deck-1", False)])

    client.download_calls.clear()
    sync.sync_decks(col, client, [("deck-1", False)])

    # boa já em col.media → não rebaixa; só a ainda-ausente é retentada
    assert client.download_calls == [item_bad["content_hash"]]


def test_stale_staging_file_swept_on_next_run(col, tmp_path):
    """T036: arquivo de staging mais velho que o TTL é removido no início do run."""
    stale = tmp_path / "orphan.png"
    stale.write_bytes(b"crash leftover")
    old = time.time() - media_mod.STAGING_TTL_SECONDS - 60
    os.utime(stale, (old, old))
    fresh = tmp_path / "recent.png"
    fresh.write_bytes(b"still valid")

    media_mod.stage_media(col, [], _FakeClient({}), tmp_path)

    assert not stale.exists()  # órfão varrido
    assert fresh.exists()  # recente preservado
