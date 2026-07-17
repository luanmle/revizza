"""US2: pre-check offline e fluxo de submit do botão "Sugerir mudança"."""

from types import SimpleNamespace

import requests

from ankihub_br.db.models import field_content_hash
from ankihub_br.gui import editor


# --- T023: pre-check offline ---


def test_no_change_when_hash_equals_baseline():
    fields = {"Frente": "P", "Verso": "R"}
    baseline = field_content_hash(fields)

    assert editor.has_local_changes(fields, baseline) is False


def test_change_detected_when_fields_differ():
    baseline = field_content_hash({"Frente": "P", "Verso": "R"})

    assert editor.has_local_changes({"Frente": "P", "Verso": "editado"}, baseline)


def test_change_assumed_without_baseline():
    # sem baseline não dá para provar no-op offline → deixa o servidor decidir
    assert editor.has_local_changes({"Frente": "P"}, None) is True


# --- T024: fluxo de submit (rascunho sempre preservado) ---


class _FakeClient:
    def __init__(self, submit_exc=None, upload_exc=None):
        self.submit_exc = submit_exc
        self.upload_exc = upload_exc
        self.submitted = []
        self.requested_media = []
        self.uploaded = []
        self.confirmed = []

    def resolve_note(self, guid):
        return {"note_id": "note-1", "deck_id": "deck-1"}

    def request_media_uploads(self, deck_id, media_items):
        self.requested_media.append((deck_id, media_items))
        return {item["content_hash"]: f"https://up/{item['content_hash']}" for item in media_items}

    def upload_signed_media(self, url, filename, content):
        if self.upload_exc:
            raise self.upload_exc
        self.uploaded.append((url, filename, content))

    def confirm_media_upload(self, deck_id, content_hash):
        self.confirmed.append((deck_id, content_hash))

    def submit_change_suggestion(self, note_id, fields, tags, category, justification):
        self.submitted.append((note_id, fields, tags, category, justification))
        if self.submit_exc:
            raise self.submit_exc
        return {"id": "sug-1"}


def _http_error(status):
    return requests.HTTPError(response=SimpleNamespace(status_code=status))


def _submit(client):
    return editor.submit_change(
        client, "guid-1", {"Verso": "novo"}, [], "erro_conteudo", "porque sim"
    )


def test_submit_success_returns_ok():
    client = _FakeClient()
    assert _submit(client) == editor.MSG_OK
    assert client.submitted[0][0] == "note-1"


def test_submit_noop_400():
    assert _submit(_FakeClient(submit_exc=_http_error(400))) == editor.MSG_NOOP


def test_submit_expired_session_401():
    assert _submit(_FakeClient(submit_exc=_http_error(401))) == editor.MSG_LOGIN


def test_submit_network_error():
    assert _submit(_FakeClient(submit_exc=requests.ConnectionError())) == editor.MSG_ERROR


def test_submit_other_http_error():
    assert _submit(_FakeClient(submit_exc=_http_error(500))) == editor.MSG_ERROR


# --- mídia referenciada sobe ANTES da sugestão ---

_BLOBS = {"a" * 64: ("img.png", b"png-bytes")}


def test_submit_uploads_media_before_suggestion():
    client = _FakeClient()
    message = editor.submit_change(
        client, "guid-1", {"Verso": '<img src="img.png">'}, [], "outro", "pq", _BLOBS
    )
    assert message == editor.MSG_OK
    assert client.requested_media == [
        ("deck-1", [{"filename": "img.png", "content_hash": "a" * 64}])
    ]
    assert client.uploaded[0][1] == "img.png"
    assert client.confirmed == [("deck-1", "a" * 64)]
    assert client.submitted  # sugestão enviada depois da mídia


def test_submit_media_upload_failure_aborts_suggestion():
    client = _FakeClient(upload_exc=_http_error(500))
    message = editor.submit_change(
        client, "guid-1", {"Verso": '<img src="img.png">'}, [], "outro", "pq", _BLOBS
    )
    assert message == editor.MSG_ERROR
    assert client.submitted == []  # nada de sugestão órfã de mídia
