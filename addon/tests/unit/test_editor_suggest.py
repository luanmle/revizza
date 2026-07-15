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
    def __init__(self, submit_exc=None):
        self.submit_exc = submit_exc
        self.submitted = []

    def resolve_note(self, guid):
        return {"note_id": "note-1"}

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
