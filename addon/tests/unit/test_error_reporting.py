import sys
from types import SimpleNamespace

from ankihub_br import entry_point
from ankihub_br import errors


def test_addon_initializes_and_captures_exception(monkeypatch):
    calls = []
    fake_sdk = SimpleNamespace(
        init=lambda **kwargs: calls.append(("init", kwargs)),
        capture_exception=lambda exc: calls.append(("capture", exc)),
    )
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sdk)

    errors.init_error_reporting("https://public@example.invalid/1")
    failure = RuntimeError("falha de teste")
    errors.report_exception(failure)

    assert calls[0] == (
        "init",
        {
            "dsn": "https://public@example.invalid/1",
            "default_integrations": False,
            "send_default_pii": False,
        },
    )
    assert calls[1] == ("capture", failure)


def test_entry_point_reads_sentry_dsn_from_anki_config(monkeypatch):
    manager = SimpleNamespace(
        getConfig=lambda package: {"sentry_dsn": "https://dsn.invalid/1"}
    )
    monkeypatch.setitem(
        sys.modules, "aqt", SimpleNamespace(mw=SimpleNamespace(addonManager=manager))
    )
    initialized = []
    monkeypatch.setattr(errors, "init_error_reporting", initialized.append)
    monkeypatch.setattr("ankihub_br.gui.setup", lambda: initialized.append("setup"))

    entry_point.run()

    assert initialized == ["https://dsn.invalid/1", "setup"]
