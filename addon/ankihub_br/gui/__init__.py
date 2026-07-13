"""Gatilhos de sincronização e menu (T043, FR-031, research.md §5).

Três gatilhos: manual (menu Ferramentas), ao abrir o perfil
(`gui_hooks.profile_did_open`) e encadeado antes do sync nativo
(monkey-patch em `AnkiQt._sync_collection_and_media` — único ponto sem hook
oficial, mesma técnica do add-on real do AnkiHub).

Este módulo importa `aqt` apenas dentro das funções: os testes headless
importam o pacote sem um Anki gráfico rodando.
"""

from pathlib import Path
from uuid import uuid4

from ..ankihub_br_client import AnkiHubBrClient
from ..db import models as state_db
from ..errors import report_exception
from ..main import compat, sync

ADDON_PACKAGE = "ankihub_br"


def setup() -> None:
    from aqt import gui_hooks, mw

    gui_hooks.profile_did_open.append(_on_profile_open)
    gui_hooks.profile_will_close.append(_on_profile_close)
    _add_menu(mw)
    _wrap_native_sync()


def _config() -> dict:
    from aqt import mw

    return mw.addonManager.getConfig(ADDON_PACKAGE) or {}


def _state_db_path() -> Path:
    user_files = Path(__file__).resolve().parent.parent / "user_files"
    user_files.mkdir(exist_ok=True)
    return user_files / "sync_state.sqlite3"


def _on_profile_open() -> None:
    state_db.init_db(_state_db_path())
    sync_all("on_anki_open")


def _on_profile_close() -> None:
    state_db.close_db()


def _add_menu(mw) -> None:
    from aqt.qt import QAction

    action = QAction("Sincronizar AnkiHub Brasil", mw)
    action.triggered.connect(lambda: sync_all("manual"))
    mw.form.menuTools.addAction(action)


def _wrap_native_sync() -> None:
    """Gatilho encadeado: sync próprio primeiro, depois o nativo (US3 AC3)."""
    from aqt.main import AnkiQt

    original = AnkiQt._sync_collection_and_media

    def chained(self, after_sync):
        try:
            sync_all("chained_native")
        except Exception as exc:  # nunca bloquear o sync nativo do usuário
            report_exception(exc)
        original(self, after_sync)

    AnkiQt._sync_collection_and_media = chained


def sync_all(trigger: str) -> None:
    """Sincroniza as assinaturas cujo gatilho `trigger` está ativo."""
    from aqt import mw
    from aqt.utils import showWarning, tooltip

    if not sync.can_sync_now():
        if trigger == "manual":
            showWarning("Aguarde 10 segundos entre sincronizações.")  # FR-032
        return
    if not compat.is_supported_anki():
        showWarning(compat.unsupported_message())  # FR-038
        return

    config = _config()
    token = config.get("token")
    if not config.get("api_base_url") or not token:
        if trigger == "manual":
            showWarning(
                "Configure a URL da API e faça login nas configurações do add-on."
            )
        return

    sync.mark_sync_started()
    try:
        client = AnkiHubBrClient(
            config["api_base_url"],
            token=token,
            anki_version=compat.anki_version(),
            sync_run_id=uuid4().hex,
        )
        deck_options = []
        for deck in client.get_subscribed_decks():
            prefs = deck.get("subscription", {})
            if trigger != "manual" and not prefs.get(f"sync_trigger_{trigger}", False):
                continue
            if trigger == "manual" and not prefs.get("sync_trigger_manual", True):
                continue
            deck_options.append(
                (deck["id"], prefs.get("delete_notes_on_removal", False))
            )
        synced = len(sync.sync_decks(mw.col, client, deck_options))
    except Exception as exc:
        report_exception(exc)
        showWarning(
            "A sincronização falhou e a coleção foi restaurada do backup. "
            f"Tente novamente. Detalhe: {exc}"
        )
        return
    finally:
        sync.mark_sync_finished()
    if synced or trigger == "manual":
        tooltip(f"AnkiHub Brasil: {synced} deck(s) sincronizado(s).")
