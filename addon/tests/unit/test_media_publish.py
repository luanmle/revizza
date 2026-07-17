"""011 US5 (T037): resiliência do publish inicial de mídia.

Retentar `publish_initial_deck` após uma tentativa parcial não pode duplicar
mídia nem re-enviar hashes já confirmados (FR-004/FR-006).
"""

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


def _add_img_note(col, deck_id, filename, data):
    Path(col.media.dir(), filename).write_bytes(data)
    note = col.new_note(col.models.current())
    note.fields = [f'<img src="{filename}">', "Resposta"]
    col.add_note(note, deck_id)
    return hashlib.sha256(data).hexdigest()


class _FakeBackend:
    """Espelha get_or_create + confirm do backend: só devolve URL para hash inédito."""

    def __init__(self, fail_upload_hash=None):
        self.confirmed: set[str] = set()  # equivale às linhas MediaFile já `ready`
        self.uploaded: list[str] = []
        self.fail_upload_hash = fail_upload_hash

    def publish_deck(self, remote_id, payload):
        # URL só para hashes que ainda não estão confirmados (get_or_create)
        urls = {
            m["content_hash"]: f"https://storage/{m['content_hash']}"
            for m in payload["media"]
            if m["content_hash"] not in self.confirmed
        }
        return {"note_count": len(payload["notes"]), "media_upload_urls": urls}

    def upload_signed_media(self, url, filename, content):
        content_hash = url.rsplit("/", 1)[1]
        if content_hash == self.fail_upload_hash:
            raise RuntimeError("crash simulado no meio do upload")
        self.uploaded.append(content_hash)

    def confirm_media_upload(self, deck_id, content_hash):
        self.confirmed.add(content_hash)


def test_retry_publish_only_uploads_unconfirmed_media(col):
    deck_id = col.decks.id("Direito")
    hash_a = _add_img_note(col, deck_id, "a.png", b"IMG-A")
    hash_b = _add_img_note(col, deck_id, "b.png", b"IMG-B")

    backend = _FakeBackend(fail_upload_hash=hash_b)
    with pytest.raises(RuntimeError):  # primeira tentativa: A sobe, B falha
        publish.publish_initial_deck(col, backend, deck_id, "remote-id")
    assert backend.confirmed == {hash_a}  # só A confirmado

    backend.fail_upload_hash = None  # rede volta
    backend.uploaded.clear()
    publish.publish_initial_deck(col, backend, deck_id, "remote-id")

    assert backend.uploaded == [hash_b]  # A não é reenviado; só o que faltava
    assert backend.confirmed == {hash_a, hash_b}  # sem duplicar A


# --- T042: regressão FR-001/FR-002/FR-003 (mantidas após T010/T011/T015) ---


def test_media_identified_only_via_note_field_scan(col):
    """FR-001: arquivo em collection.media não referenciado por nota fica de fora."""
    deck_id = col.decks.id("Direito")
    _add_img_note(col, deck_id, "usada.png", b"REFERENCIADA")
    # arquivo órfão na pasta de mídia, sem <img src> em nenhuma nota
    Path(col.media.dir(), "orfa.png").write_bytes(b"NAO REFERENCIADA")

    payload, blobs = publish.build_publish_payload(col, deck_id)

    filenames = [m["filename"] for m in payload["media"]]
    assert filenames == ["usada.png"]  # só a referenciada
    assert "orfa.png" not in {name for name, _ in blobs.values()}


def test_media_deduplicated_by_hash_within_payload(col):
    """FR-002: duas notas com o mesmo conteúdo geram uma única entrada de mídia."""
    deck_id = col.decks.id("Direito")
    same = b"CONTEUDO IDENTICO"
    hash_a = _add_img_note(col, deck_id, "copia1.png", same)
    hash_b = _add_img_note(col, deck_id, "copia2.png", same)
    assert hash_a == hash_b  # mesmo conteúdo, mesmo hash

    payload, blobs = publish.build_publish_payload(col, deck_id)

    hashes = [m["content_hash"] for m in payload["media"]]
    assert hashes == [hash_a]  # dedup por hash
    assert list(blobs) == [hash_a]


def test_upload_signed_media_sends_no_bearer(monkeypatch):
    """FR-003: upload ao storage assinado nunca vaza o Bearer da API."""
    from ankihub_br.ankihub_br_client import client as client_mod

    captured = {}

    def fake_put(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs

        class _Resp:
            def raise_for_status(self):
                return None

        return _Resp()

    monkeypatch.setattr(client_mod.requests, "put", fake_put)
    api = client_mod.AnkiHubBrClient("https://api.example.com", token="segredo")
    api.upload_signed_media("https://storage/abc", "x.png", b"bytes")

    # não passa por self.session (que carrega o Authorization) nem manda headers
    headers = captured["kwargs"].get("headers", {})
    assert "Authorization" not in headers
    assert "segredo" not in str(captured["kwargs"])
