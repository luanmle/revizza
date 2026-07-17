"""Gatilhos de sincronização e menu Revizza.

Três gatilhos: manual, ao abrir o perfil
(`gui_hooks.profile_did_open`) e encadeado antes do sync nativo
(monkey-patch em `AnkiQt._sync_collection_and_media` — único ponto sem hook
oficial, mesma técnica do add-on real do AnkiHub).

Este módulo importa `aqt` apenas dentro das funções: os testes headless
importam o pacote sem um Anki gráfico rodando.
"""

from functools import partial
from pathlib import Path
from uuid import uuid4

import requests

from .. import auth
from ..ankihub_br_client import AnkiHubBrClient
from ..db import models as state_db
from ..errors import report_exception
from ..main import compat, publish, sync
from ..main.constants import connection_settings

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
_revizza_menu = None
_pending_sync_count = 0  # cache do último client.get_subscribed_decks() (T024)


def menu_item_states(
    logged_in: bool, pending_count: int = 0
) -> tuple[tuple[str, bool], ...]:
    """Estado puro dos cinco itens do menu (T155)."""
    decks_label = "Decks inscritos"
    if pending_count > 0:
        decks_label += f" ({pending_count})"
    return (
        ("Sair" if logged_in else "Entrar", True),
        ("Sincronizar agora", logged_in),
        (decks_label, logged_in),
        ("Criar deck Revizza", logged_in),
        ("Testar conexão", True),
    )


def sync_failure_message(exc: Exception) -> str:
    """Mensagem de erro de `sync_all` (bug: invalid-refresh-token).

    `auth.AuthError` é levantado por `ensure_access_token` antes de qualquer
    escrita na coleção — nenhum backup foi criado/restaurado, então a sessão
    expirada/revogada exige novo login, não uma nova tentativa de sync.
    """
    if isinstance(exc, auth.AuthError):
        return f"Sessão do Revizza expirada. Faça login novamente. Detalhe: {exc}"
    return (
        "A sincronização falhou e a coleção foi restaurada do backup. "
        f"Tente novamente. Detalhe: {exc}"
    )


def deck_group_title(deck: dict) -> str:
    """Título do QGroupBox de um deck em 'Decks inscritos' (T026 — marca pendência)."""
    title = deck["name"]
    if deck.get("pending_sync"):
        title += " ⚠ pendente"
    return title


def connection_status_message(result: dict[str, bool | None]) -> str:
    lines = ["API ok" if result["api_ok"] else "API indisponível"]
    if result["session_ok"] is not None:
        lines.append("Sessão ok" if result["session_ok"] else "Sessão expirada")
    return "\n".join(lines)


def _has_session(config: dict) -> bool:
    return bool(config.get("token") or config.get("refresh_token"))


def _run_network(operation, success, failure) -> None:
    """Executa HTTP fora da thread Qt; callbacks voltam à thread principal."""
    from aqt import mw
    from aqt.operations import QueryOp

    def run(_collection):
        return operation()

    (
        QueryOp(parent=mw, op=run, success=success)
        .failure(failure)
        .without_collection()
        .run_in_background()
    )


def _show_operation_error(prefix: str, exc: Exception) -> None:
    from aqt.utils import showWarning

    report_exception(exc)
    showWarning(f"{prefix}: {exc}")


def setup() -> None:
    from aqt import gui_hooks, mw

    from . import editor, reviewer

    gui_hooks.profile_did_open.append(_on_profile_open)
    gui_hooks.profile_will_close.append(_on_profile_close)
    _add_menu(mw)
    _wrap_native_sync()
    reviewer.setup()
    editor.setup()


def _config() -> dict:
    from aqt import mw

    return mw.addonManager.getConfig(ADDON_PACKAGE) or {}


def _write_config(config: dict) -> None:
    from aqt import mw

    mw.addonManager.writeConfig(ADDON_PACKAGE, config)


def _state_db_path() -> Path:
    # Por perfil: o `since_mod` de um perfil não pode vazar para outro — um cache
    # global faz o primeiro sync de um perfil novo voltar delta vazio (sem cartões).
    from aqt import mw

    return Path(mw.pm.profileFolder()) / "ankihub_br_sync_state.sqlite3"


def _on_profile_open() -> None:
    state_db.init_db(_state_db_path())
    sync_all("on_anki_open")


def _on_profile_close() -> None:
    state_db.close_db()


def _add_menu(mw) -> None:
    from aqt.qt import QMenu, qconnect

    global _revizza_menu
    _revizza_menu = QMenu("&Revizza", parent=mw)
    _revizza_menu.addAction("Carregando…").setEnabled(False)
    mw.form.menubar.addMenu(_revizza_menu)
    qconnect(_revizza_menu.aboutToShow, _refresh_menu)


def _refresh_menu() -> None:
    from aqt.qt import qconnect

    if _revizza_menu is None:
        return
    _revizza_menu.clear()
    logged_in = _has_session(_config())
    callbacks = (
        show_sign_out if logged_in else show_login,
        _sync_now,
        show_subscribed_decks,
        show_publish,
        show_test_connection,
    )
    states = menu_item_states(logged_in, pending_count=_pending_sync_count)
    for (label, enabled), callback in zip(states, callbacks):
        action = _revizza_menu.addAction(label)
        action.setEnabled(enabled)
        qconnect(action.triggered, callback)


def _sync_now() -> None:
    sync_all("manual")


def show_sign_out() -> None:
    from aqt.utils import tooltip

    config = _config()
    auth.sign_out(config)
    _write_config(config)
    tooltip("Sessão Revizza encerrada.")


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

    dialog = QDialog(mw)
    dialog.setWindowTitle("Entrar no Revizza")
    layout = QVBoxLayout(dialog)
    description = QLabel(
        "Use a mesma conta da plataforma web. A senha não será armazenada."
    )
    description.setWordWrap(True)
    layout.addWidget(description)

    form = QFormLayout()
    email = QLineEdit()
    email.setPlaceholderText("voce@exemplo.com")
    password = QLineEdit()
    password.setEchoMode(QLineEdit.EchoMode.Password)
    form.addRow("E-mail", email)
    form.addRow("Senha", password)
    layout.addLayout(form)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Entrar")
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if not dialog.exec():
        return
    email_value = email.text().strip()
    password_value = password.text()
    if not email_value or not password_value:
        showWarning("Informe e-mail e senha.")
        return

    config = _config()
    settings = connection_settings(config)

    def sign_in():
        session = auth.sign_in(
            settings["supabase_url"],
            settings["supabase_anon_key"],
            email_value,
            password_value,
        )
        updated_config = dict(config)
        auth.store_session(updated_config, session)
        return updated_config

    def signed_in(updated_config):
        _write_config(updated_config)
        tooltip("Login realizado. Revizza já pode sincronizar seus decks.")

    _run_network(
        sign_in,
        signed_in,
        partial(_show_operation_error, "Não foi possível entrar"),
    )


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
    if not _has_session(config):
        showWarning("Faça login no Revizza antes de criar um deck.")
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
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
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
            connection_settings(config)["api_base_url"],
            token=token,
            anki_version=compat.anki_version(),
        )
        # leitura da coleção na thread Qt; upload vai para background (US4/T029)
        payload, media_blobs = publish.build_publish_payload(
            mw.col,
            local_deck_id,
            [item.strip() for item in tags.text().split(",") if item.strip()],
        )
    except Exception as exc:
        report_exception(exc)
        showWarning(f"A importação falhou: {exc}")
        return

    def publish_failed(exc: Exception) -> None:
        report_exception(exc)
        if (
            isinstance(exc, requests.HTTPError)
            and exc.response is not None
            and exc.response.status_code == 409
        ):
            showWarning(
                "O deck já existe na plataforma. A importação não foi repetida; "
                "use sugestões na web para alterá-lo."
            )
        else:
            showWarning(f"A importação falhou: {exc}")

    def publish_done(result) -> None:
        published[str(local_deck_id)]["status"] = "published"
        _write_config(config)
        tooltip(f"Deck importado com {result['note_count']} nota(s).")

    _run_network(
        lambda: publish.publish_uploads(
            client, remote_deck_id, payload, media_blobs
        ),
        publish_done,
        publish_failed,
    )


def _save_subscriptions(
    client, preferences_by_deck: dict, unsubscribed_deck_ids: set[str]
) -> None:
    for deck_id, preferences in preferences_by_deck.items():
        if deck_id not in unsubscribed_deck_ids:
            client.update_subscription_preferences(deck_id, preferences)
    for deck_id in sorted(unsubscribed_deck_ids):
        client.unsubscribe(deck_id)


def show_subscribed_decks() -> None:
    from aqt.utils import showInfo, showWarning

    config = _config()
    if not _has_session(config):
        showWarning("Faça login no Revizza para ver seus decks inscritos.")
        return

    def load_decks():
        updated_config = dict(config)
        token, refreshed = auth.ensure_access_token(updated_config)
        client = AnkiHubBrClient(
            connection_settings(updated_config)["api_base_url"],
            token=token,
            anki_version=compat.anki_version(),
        )
        return updated_config if refreshed else None, client.get_subscribed_decks()

    def decks_loaded(result):
        global _pending_sync_count
        updated_config, decks = result
        if updated_config is not None:
            _write_config(updated_config)
        _pending_sync_count = sum(1 for deck in decks if deck.get("pending_sync"))
        if not decks:
            showInfo("Você ainda não assina nenhum deck.")
            return
        _open_subscribed_decks_dialog(decks)

    _run_network(
        load_decks,
        decks_loaded,
        partial(_show_operation_error, "Não foi possível carregar os decks inscritos"),
    )


def _open_subscribed_decks_dialog(decks: list[dict]) -> None:
    from aqt import mw
    from aqt.qt import (
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QGroupBox,
        QLabel,
        QPushButton,
        QScrollArea,
        QVBoxLayout,
        QWidget,
        qconnect,
    )
    from aqt.utils import askUser, tooltip

    dialog = QDialog(mw)
    dialog.setWindowTitle("Decks inscritos — Revizza")
    dialog.resize(480, 520)
    layout = QVBoxLayout(dialog)
    description = QLabel(
        "Ajuste a sincronização ou cancele uma inscrição. "
        "Novas inscrições são feitas na plataforma web."
    )
    description.setWordWrap(True)
    layout.addWidget(description)

    scroll = QScrollArea(dialog)
    scroll.setWidgetResizable(True)
    deck_container = QWidget()
    deck_layout = QVBoxLayout(deck_container)
    controls_by_deck = {}
    unsubscribed_deck_ids: set[str] = set()

    def mark_unsubscribe(
        deck_id: str, deck_name: str, controls: dict, button: QPushButton
    ) -> None:
        if not askUser(
            f'Cancelar a inscrição em "{deck_name}"?',
            parent=dialog,
        ):
            return
        unsubscribed_deck_ids.add(deck_id)
        for control in controls.values():
            control.setEnabled(False)
        button.setText("Cancelamento marcado")
        button.setEnabled(False)

    for deck in decks:
        group = QGroupBox(deck_group_title(deck))
        group_layout = QVBoxLayout(group)
        preferences = deck.get("subscription", {})
        controls = {}
        for name, label, default in PREFERENCE_FIELDS:
            control = QCheckBox(label)
            control.setChecked(bool(preferences.get(name, default)))
            group_layout.addWidget(control)
            controls[name] = control
        deck_id = str(deck["id"])
        controls_by_deck[deck_id] = controls
        unsubscribe_button = QPushButton("Cancelar inscrição")
        qconnect(
            unsubscribe_button.clicked,
            partial(
                mark_unsubscribe,
                deck_id,
                deck["name"],
                controls,
                unsubscribe_button,
            ),
        )
        group_layout.addWidget(unsubscribe_button)
        deck_layout.addWidget(group)
    deck_layout.addStretch()
    scroll.setWidget(deck_container)
    layout.addWidget(scroll)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    buttons.button(QDialogButtonBox.StandardButton.Save).setText("Salvar")
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if not dialog.exec():
        return
    preferences_by_deck = {
        deck_id: {name: control.isChecked() for name, control in controls.items()}
        for deck_id, controls in controls_by_deck.items()
    }
    config = _config()

    def save_changes():
        updated_config = dict(config)
        token, refreshed = auth.ensure_access_token(updated_config)
        client = AnkiHubBrClient(
            connection_settings(updated_config)["api_base_url"],
            token=token,
            anki_version=compat.anki_version(),
        )
        _save_subscriptions(client, preferences_by_deck, unsubscribed_deck_ids)
        return updated_config if refreshed else None

    def changes_saved(updated_config):
        if updated_config is not None:
            _write_config(updated_config)
        tooltip("Decks inscritos atualizados.")

    _run_network(
        save_changes,
        changes_saved,
        partial(_show_operation_error, "Não foi possível salvar os decks inscritos"),
    )


def show_test_connection() -> None:
    from aqt.utils import showInfo

    config = _config()

    def test_connection():
        client = AnkiHubBrClient(
            connection_settings(config)["api_base_url"],
            token=config.get("token") or None,
            anki_version=compat.anki_version(),
        )
        return client.test_connection()

    def connection_tested(result):
        showInfo(connection_status_message(result))

    _run_network(
        test_connection,
        connection_tested,
        partial(_show_operation_error, "Não foi possível testar a conexão"),
    )


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
    if not _has_session(config):
        if trigger == "manual":
            showWarning("Faça login no Revizza antes de sincronizar.")
        return

    from aqt.operations import QueryOp

    from ..main.constants import media_concurrency

    def _fail(exc: Exception) -> None:
        sync.mark_sync_finished()
        report_exception(exc)
        if isinstance(exc, auth.AuthError):
            auth.sign_out(config)
            _write_config(config)
        showWarning(sync_failure_message(exc))

    def _report_progress(done: int, total: int) -> None:
        # T031: contagem visível da fase de staging, empurrada para a thread Qt.
        if total:
            mw.taskman.run_on_main(
                lambda: mw.progress.update(
                    label=f"Revizza: mídia {done}/{total}", value=done, max=total
                )
            )

    def _should_cancel() -> bool:  # T032: botão Cancelar do diálogo de progresso
        return mw.progress.want_cancel()

    sync.mark_sync_started()
    try:
        token, refreshed = auth.ensure_access_token(config)
        if refreshed:
            _write_config(config)
    except Exception as exc:  # falha de auth antes de qualquer trabalho de rede
        _fail(exc)
        return
    client = AnkiHubBrClient(
        connection_settings(config)["api_base_url"],
        token=token,
        anki_version=compat.anki_version(),
        sync_run_id=uuid4().hex,
    )

    def phase_network(_col):
        # Fase 1 (US4/T028): assinaturas + download/validação da mídia, sem
        # travar a coleção — o Anki fica responsivo durante downloads pesados.
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
        return sync.prepare_run(
            mw.col,
            client,
            deck_options,
            concurrency=media_concurrency(config),
            should_cancel=_should_cancel,
            on_progress=_report_progress,
        )

    def phase_apply(prepared):
        # Fase 2 (US4/T028): escreve notas + commit da mídia sob backup.
        def op(_col):
            return len(sync.commit_run(mw.col, client, prepared))

        def done(synced):
            sync.mark_sync_finished()
            if synced or trigger == "manual":
                tooltip(f"Revizza: {synced} deck(s) sincronizado(s).")

        QueryOp(parent=mw, op=op, success=done).failure(
            _fail
        ).with_progress("Revizza: aplicando alterações…").run_in_background()

    (
        QueryOp(parent=mw, op=phase_network, success=phase_apply)
        .failure(_fail)
        .without_collection()
        .with_progress("Revizza: sincronizando mídia…")
        .run_in_background()
    )
