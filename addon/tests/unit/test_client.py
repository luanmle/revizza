from ankihub_br.ankihub_br_client import AnkiHubBrClient
from ankihub_br.ankihub_br_client import client as client_module
from ankihub_br.gui import _save_subscriptions


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


def test_subscription_changes_are_saved_per_deck(monkeypatch):
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

    unsubscribed = []
    monkeypatch.setattr(client, "unsubscribe", unsubscribed.append)

    _save_subscriptions(
        client,
        {
            "deck-1": {
                "sync_trigger_manual": True,
                "sync_trigger_on_anki_open": False,
                "sync_trigger_chained_native": True,
                "delete_notes_on_removal": False,
            },
            "deck-2": {},
        },
        {"deck-2"},
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
    assert unsubscribed == ["deck-2"]


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

    client.upload_signed_media(
        "https://storage.example/upload?token=signed", "a.png", b"png"
    )

    assert calls == [
        (
            "https://storage.example/upload?token=signed",
            {
                "files": {"file": ("a.png", b"png", "application/octet-stream")},
                "timeout": 30,
            },
        )
    ]


def test_connection_without_session_only_checks_health(monkeypatch):
    client = AnkiHubBrClient("https://api.example.com")
    calls = []
    monkeypatch.setattr(client, "get", lambda path: calls.append(path))

    assert client.test_connection() == {"api_ok": True, "session_ok": None}
    assert calls == ["/health/"]


def test_connection_keeps_api_and_expired_session_signals_distinct(monkeypatch):
    client = AnkiHubBrClient("https://api.example.com", token="expired")

    def get(path):
        if path == "/accounts/me/":
            raise client_module.requests.HTTPError("401")

    monkeypatch.setattr(client, "get", get)

    assert client.test_connection() == {"api_ok": True, "session_ok": False}


def test_connection_with_valid_session_checks_both_endpoints(monkeypatch):
    client = AnkiHubBrClient("https://api.example.com", token="access")
    calls = []
    monkeypatch.setattr(client, "get", lambda path: calls.append(path))

    assert client.test_connection() == {"api_ok": True, "session_ok": True}
    assert calls == ["/health/", "/accounts/me/"]


def test_connection_reports_unreachable_api(monkeypatch):
    client = AnkiHubBrClient("https://api.example.com", token="access")

    def get(_path):
        raise client_module.requests.ConnectionError("offline")

    monkeypatch.setattr(client, "get", get)

    assert client.test_connection() == {"api_ok": False, "session_ok": None}


def test_unsubscribe_deletes_current_subscription(monkeypatch):
    client = AnkiHubBrClient("https://api.example.com", token="access")
    calls = []
    monkeypatch.setattr(client, "delete", lambda path: calls.append(path))

    client.unsubscribe("deck-1")

    assert calls == ["/decks/deck-1/subscriptions/me/"]
