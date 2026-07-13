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

import requests

from .. import auth
from ..ankihub_br_client import AnkiHubBrClient
from ..db import models as state_db
from ..errors import report_exception
from ..main import compat, publish, sync

ADDON_PACKAGE = "ankihub_br"
PREFERENCE_FIELDS = (
    ("sync_trigger_manual", "Permitir sincronização manual", True),
    (
        "sync_trigger_on_anki_open",
        "Sincronizar automaticamente ao abrir o Anki",
        False,
    ),
    (
        "sync_trigger_chained_native",
        "Sincronizar antes do sync nativo do Anki",
        False,
    ),
    (
        "delete_notes_on_removal",
        "Apagar notas removidas (desmarcado: apenas marcar)",
        False,
    ),
)


def setup() -> None:
    from aqt import gui_hooks, mw

    gui_hooks.profile_did_open.append(_on_profile_open)
    gui_hooks.profile_will_close.append(_on_profile_close)
    _add_menu(mw)
    _wrap_native_sync()


def _config() -> dict:
    from aqt import mw

    return mw.addonManager.getConfig(ADDON_PACKAGE) or {}


def _write_config(config: dict) -> None:
    from aqt import mw

    mw.addonManager.writeConfig(ADDON_PACKAGE, config)


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

    login_action = QAction("Entrar no AnkiHub Brasil…", mw)
    login_action.triggered.connect(show_login)
    mw.form.menuTools.addAction(login_action)

    publish_action = QAction("Importar deck inicial para o AnkiHub Brasil…", mw)
    publish_action.triggered.connect(show_publish)
    mw.form.menuTools.addAction(publish_action)

    action = QAction("Sincronizar AnkiHub Brasil", mw)
    action.triggered.connect(lambda: sync_all("manual"))
    mw.form.menuTools.addAction(action)

    preferences_action = QAction("Preferências do AnkiHub Brasil…", mw)
    preferences_action.triggered.connect(show_preferences)
    mw.form.menuTools.addAction(preferences_action)


def show_login() -> None:
    from aqt import mw
    from aqt.qt import (
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QLabel,
        QLineEdit,
        QVBoxLayout,
    )
    from aqt.utils import showWarning, tooltip

    config = _config()
    dialog = QDialog(mw)
    dialog.setWindowTitle("Entrar no AnkiHub Brasil")
    layout = QVBoxLayout(dialog)
    description = QLabel(
        "Use a mesma conta da plataforma web. A senha não será armazenada."
    )
    description.setWordWrap(True)
    layout.addWidget(description)

    form = QFormLayout()
    api_url = QLineEdit(config.get("api_base_url", ""))
    supabase_url = QLineEdit(config.get("supabase_url", ""))
    anon_key = QLineEdit(config.get("supabase_anon_key", ""))
    email = QLineEdit()
    email.setPlaceholderText("voce@exemplo.com")
    password = QLineEdit()
    password.setEchoMode(QLineEdit.EchoMode.Password)
    form.addRow("URL da API", api_url)
    form.addRow("URL do Supabase", supabase_url)
    form.addRow("Chave pública do Supabase", anon_key)
    form.addRow("E-mail", email)
    form.addRow("Senha", password)
    layout.addLayout(form)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok
        | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Entrar")
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if not dialog.exec():
        return
    try:
        session = auth.sign_in(
            supabase_url.text().strip(),
            anon_key.text().strip(),
            email.text().strip(),
            password.text(),
        )
        config.update(
            api_base_url=api_url.text().strip(),
            supabase_url=supabase_url.text().strip(),
            supabase_anon_key=anon_key.text().strip(),
        )
        auth.store_session(config, session)
        _write_config(config)
    except Exception as exc:
        report_exception(exc)
        showWarning(str(exc))
        return
    tooltip("Login realizado. O add-on já pode sincronizar seus decks.")


def show_publish() -> None:
    from aqt import mw
    from aqt.qt import (
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QLabel,
        QLineEdit,
        QVBoxLayout,
    )
    from aqt.utils import askUser, showWarning, tooltip

    config = _config()
    if not config.get("api_base_url"):
        showWarning("Configure a URL da API e faça login antes de importar.")
        return
    decks = [
        deck
        for deck in mw.col.decks.all_names_and_ids(include_filtered=False)
        if "::" not in deck.name
    ]
    if not decks:
        showWarning("Nenhum deck local disponível para importar.")
        return

    dialog = QDialog(mw)
    dialog.setWindowTitle("Importação inicial de deck")
    layout = QVBoxLayout(dialog)
    warning = QLabel(
        "Esta operação cria o primeiro snapshot oficial uma única vez. "
        "Mudanças futuras deverão passar por sugestões na web."
    )
    warning.setWordWrap(True)
    layout.addWidget(warning)
    form = QFormLayout()
    deck_box = QComboBox()
    for deck in decks:
        deck_box.addItem(deck.name, int(deck.id))
    tags = QLineEdit()
    tags.setPlaceholderText("direito, concurso")
    form.addRow("Deck", deck_box)
    form.addRow("Tags de assunto", tags)
    layout.addLayout(form)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok
        | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Importar uma vez")
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    if not dialog.exec():
        return

    local_deck_id = int(deck_box.currentData())
    published = config.setdefault("published_decks", {})
    mapping = published.get(str(local_deck_id))
    if mapping and mapping.get("status") == "published":
        showWarning(
            "Este deck local já foi importado. Edite o conteúdo pela plataforma web."
        )
        return
    if not askUser(
        "Confirma a importação única? O add-on nunca republicará este deck.",
        parent=mw,
    ):
        return

    remote_deck_id = mapping.get("remote_deck_id") if mapping else str(uuid4())
    published[str(local_deck_id)] = {
        "remote_deck_id": remote_deck_id,
        "status": "pending",
    }
    _write_config(config)
    try:
        token, refreshed = auth.ensure_access_token(config)
        if refreshed:
            _write_config(config)
        client = AnkiHubBrClient(
            config["api_base_url"],
            token=token,
            anki_version=compat.anki_version(),
        )
        result = publish.publish_initial_deck(
            mw.col,
            client,
            local_deck_id,
            remote_deck_id,
            [item.strip() for item in tags.text().split(",") if item.strip()],
        )
    except requests.HTTPError as exc:
        report_exception(exc)
        if exc.response is not None and exc.response.status_code == 409:
            showWarning(
                "O deck já existe na plataforma. A importação não foi repetida; "
                "use sugestões na web para alterá-lo."
            )
        else:
            showWarning(f"A importação falhou: {exc}")
        return
    except Exception as exc:
        report_exception(exc)
        showWarning(f"A importação falhou: {exc}")
        return

    published[str(local_deck_id)]["status"] = "published"
    _write_config(config)
    tooltip(f"Deck importado com {result['note_count']} nota(s).")


def _save_preferences(client, controls_by_deck: dict) -> None:
    for deck_id, controls in controls_by_deck.items():
        client.update_subscription_preferences(
            deck_id, {name: control.isChecked() for name, control in controls.items()}
        )


def show_preferences() -> None:
    from aqt import mw
    from aqt.qt import (
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QGroupBox,
        QLabel,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )
    from aqt.utils import showInfo, showWarning, tooltip

    config = _config()
    if not config.get("api_base_url"):
        showWarning(
            "Configure a URL da API e faça login nas configurações do add-on."
        )
        return

    try:
        token, refreshed = auth.ensure_access_token(config)
        if refreshed:
            _write_config(config)
        client = AnkiHubBrClient(
            config["api_base_url"],
            token=token,
            anki_version=compat.anki_version(),
        )
        decks = client.get_subscribed_decks()
    except Exception as exc:
        report_exception(exc)
        showWarning(f"Não foi possível carregar as preferências: {exc}")
        return
    if not decks:
        showInfo("Você ainda não assina nenhum deck.")
        return

    dialog = QDialog(mw)
    dialog.setWindowTitle("Preferências do AnkiHub Brasil")
    dialog.resize(480, 520)
    layout = QVBoxLayout(dialog)
    description = QLabel("Escolha como cada deck assinado será sincronizado.")
    description.setWordWrap(True)
    layout.addWidget(description)

    scroll = QScrollArea(dialog)
    scroll.setWidgetResizable(True)
    deck_container = QWidget()
    deck_layout = QVBoxLayout(deck_container)
    controls_by_deck = {}
    for deck in decks:
        group = QGroupBox(deck["name"])
        group_layout = QVBoxLayout(group)
        preferences = deck.get("subscription", {})
        controls = {}
        for name, label, default in PREFERENCE_FIELDS:
            control = QCheckBox(label)
            control.setChecked(bool(preferences.get(name, default)))
            group_layout.addWidget(control)
            controls[name] = control
        controls_by_deck[str(deck["id"])] = controls
        deck_layout.addWidget(group)
    deck_layout.addStretch()
    scroll.setWidget(deck_container)
    layout.addWidget(scroll)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save
        | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    buttons.button(QDialogButtonBox.StandardButton.Save).setText("Salvar")
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if not dialog.exec():
        return
    try:
        _save_preferences(client, controls_by_deck)
    except Exception as exc:
        report_exception(exc)
        showWarning(f"Não foi possível salvar as preferências: {exc}")
        return
    tooltip("Preferências de sincronização salvas.")


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
    if not config.get("api_base_url"):
        if trigger == "manual":
            showWarning(
                "Configure a URL da API e faça login nas configurações do add-on."
            )
        return

    sync.mark_sync_started()
    try:
        token, refreshed = auth.ensure_access_token(config)
        if refreshed:
            _write_config(config)
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
