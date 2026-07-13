from ankihub_br.ankihub_br_client import AnkiHubBrClient
from ankihub_br.ankihub_br_client import client as client_module
from ankihub_br.gui import _save_preferences


def test_client_rejects_non_https_base_url():
    try:
        AnkiHubBrClient("http://api.example.com")
    except ValueError as exc:
        assert str(exc) == "A URL da API deve usar HTTPS."
    else:
        raise AssertionError("HTTP API URL was accepted")


def test_client_sends_sync_run_id():
    client = AnkiHubBrClient("https://api.example.com", sync_run_id="run-1")

    assert client.session.headers["X-Sync-Run-ID"] == "run-1"


def test_preferences_are_patched_per_subscription(monkeypatch):
    class Control:
        def __init__(self, checked):
            self.checked = checked

        def isChecked(self):
            return self.checked

    class Response:
        def json(self):
            return {"saved": True}

    client = AnkiHubBrClient("https://api.example.com")
    calls = []
    monkeypatch.setattr(
        client,
        "patch",
        lambda path, **kwargs: calls.append((path, kwargs["json"])) or Response(),
    )

    _save_preferences(
        client,
        {
            "deck-1": {
                "sync_trigger_manual": Control(True),
                "sync_trigger_on_anki_open": Control(False),
                "sync_trigger_chained_native": Control(True),
                "delete_notes_on_removal": Control(False),
            }
        },
    )

    assert calls == [
        (
            "/decks/deck-1/subscriptions/me/",
            {
                "sync_trigger_manual": True,
                "sync_trigger_on_anki_open": False,
                "sync_trigger_chained_native": True,
                "delete_notes_on_removal": False,
            },
        )
    ]


def test_signed_media_upload_does_not_send_api_authorization(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        client_module.requests,
        "put",
        lambda url, **kwargs: calls.append((url, kwargs)) or Response(),
    )
    client = AnkiHubBrClient("https://api.example.com", token="secret")

    client.upload_signed_media("https://storage.example/upload?token=signed", "a.png", b"png")

    assert calls == [
        (
            "https://storage.example/upload?token=signed",
            {
                "files": {
                    "file": ("a.png", b"png", "application/octet-stream")
                },
                "timeout": 30,
            },
        )
    ]
