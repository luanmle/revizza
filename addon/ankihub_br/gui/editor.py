"""Botão "Sugerir mudança" no editor de notas (contracts/addon-actions.md, US2).

Habilitado só quando o GUID da nota aberta está no cache de sync. Faz o
pre-check offline (hash dos campos atuais vs. `field_hash` do último sync) e
submete a sugestão pelo pipeline existente — é uma proposta, nunca um push
direto (Princípio II). Não lê nem escreve scheduling (Princípio VIII).

`aqt` é importado dentro das funções: os testes headless importam o módulo sem
um Anki gráfico rodando.
"""

import requests

from ..ankihub_br_client import AnkiHubBrClient
from ..db.models import deck_id_for_guid, field_content_hash, field_hash_for_guid
from ..errors import report_exception
from ..main import compat
from ..main.constants import connection_settings

_BUTTON_ID = "revizza-suggest-btn"

# Espelha as categorias da web (Suggestion.ChangeCategory / FR-013).
CATEGORIES = (
    ("conteudo_atualizado", "Conteúdo atualizado"),
    ("ortografia_gramatica", "Ortografia/Gramática"),
    ("erro_conteudo", "Erro de conteúdo"),
    ("nova_tag", "Nova tag"),
    ("tag_atualizada", "Tag atualizada"),
    ("outro", "Outro"),
)

MSG_OK = "Sugestão enviada. Ela já aparece na aba Sugestões da comunidade."
MSG_NOOP = "Nada a sugerir: a nota não mudou em relação à versão do Revizza."
MSG_LOGIN = "Sessão do Revizza expirada. Entre novamente — seu rascunho foi mantido."
MSG_ERROR = "Não foi possível enviar a sugestão. Tente novamente — rascunho mantido."


def is_suggest_enabled(note) -> bool:
    """Regra de visibilidade: nota aberta pertence a um deck Revizza inscrito."""
    if note is None:
        return False
    return deck_id_for_guid(note.guid) is not None


def has_local_changes(current_fields: dict, stored_hash: str | None) -> bool:
    """Pre-check offline: há algo a sugerir? (FR-008).

    Sem baseline (`stored_hash` None) não dá para provar no-op offline — deixa o
    servidor decidir. Igual ao baseline → nada mudou.
    """
    if stored_hash is None:
        return True
    return field_content_hash(current_fields) != stored_hash


def submit_change(
    client,
    guid: str,
    fields: dict,
    tags: list[str],
    category: str,
    justification: str,
) -> str:
    """Resolve o GUID e submete a sugestão. Retorna a mensagem ao usuário.

    Nunca levanta por erro HTTP — o rascunho do editor é sempre preservado porque
    este fluxo jamais toca os campos abertos.
    """
    try:
        resolved = client.resolve_note(guid)
        client.submit_change_suggestion(
            resolved["note_id"], fields, tags, category, justification
        )
    except requests.HTTPError as exc:
        code = getattr(exc.response, "status_code", None)
        if code == 400:  # is_noop do backend
            return MSG_NOOP
        if code == 401:
            return MSG_LOGIN
        return MSG_ERROR
    except requests.RequestException:
        return MSG_ERROR
    return MSG_OK


# --- Cola com o Qt (não coberta por teste headless) ---


def _config() -> dict:
    from aqt import mw

    return mw.addonManager.getConfig("ankihub_br") or {}


def _on_init_buttons(buttons, editor):
    buttons.append(
        editor.addButton(
            icon=None,
            cmd="revizza_suggest",
            func=_on_click,
            tip="Sugerir mudança desta nota no Revizza",
            label="Sugerir mudança",
            id=_BUTTON_ID,
            disables=False,
        )
    )
    return buttons


def _on_load_note(editor) -> None:
    display = "" if is_suggest_enabled(editor.note) else "none"
    editor.web.eval(
        f'var b=document.getElementById("{_BUTTON_ID}"); '
        f'if(b) b.style.display="{display}";'
    )


def _ask_category_and_justification(parent):
    from aqt.qt import (
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QLabel,
        QPlainTextEdit,
        QVBoxLayout,
    )
    from aqt.utils import showWarning

    dialog = QDialog(parent)
    dialog.setWindowTitle("Sugerir mudança — Revizza")
    layout = QVBoxLayout(dialog)
    intro = QLabel(
        "Sua edição vira uma sugestão pendente de moderação. "
        "O deck oficial só muda quando um moderador aceitar."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    form = QFormLayout()
    category_box = QComboBox()
    for value, label in CATEGORIES:
        category_box.addItem(label, value)
    justification = QPlainTextEdit()
    justification.setPlaceholderText("Por que esta mudança? (obrigatório)")
    form.addRow("Tipo de mudança", category_box)
    form.addRow("Justificativa", justification)
    layout.addLayout(form)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Enviar sugestão")
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if not dialog.exec():
        return None
    text = justification.toPlainText().strip()
    if not text:
        showWarning("A justificativa é obrigatória.")
        return None
    return category_box.currentData(), text


def _on_click(editor) -> None:
    from aqt.utils import tooltip

    note = editor.note
    if note is None:
        return
    current_fields = dict(note.items())
    if not has_local_changes(current_fields, field_hash_for_guid(note.guid)):
        tooltip(MSG_NOOP)
        return
    result = _ask_category_and_justification(editor.parentWindow)
    if result is None:
        return
    category, justification = result
    _submit_off_thread(editor, note.guid, current_fields, category, justification)


def _submit_off_thread(editor, guid, fields, category, justification) -> None:
    from aqt import mw
    from aqt.operations import QueryOp
    from aqt.utils import showWarning, tooltip

    from .. import auth

    config = _config()

    def op(_collection):
        updated = dict(config)
        token, refreshed = auth.ensure_access_token(updated)
        client = AnkiHubBrClient(
            connection_settings(updated)["api_base_url"],
            token=token,
            anki_version=compat.anki_version(),
        )
        message = submit_change(client, guid, fields, [], category, justification)
        return (updated if refreshed else None, message)

    def done(result):
        updated, message = result
        if updated is not None:
            mw.addonManager.writeConfig("ankihub_br", updated)
        tooltip(message)

    def failed(exc):
        report_exception(exc)
        showWarning(MSG_LOGIN if isinstance(exc, auth.AuthError) else MSG_ERROR)

    (
        QueryOp(parent=editor.parentWindow, op=op, success=done)
        .failure(failed)
        .without_collection()
        .run_in_background()
    )


def setup() -> None:
    from aqt import gui_hooks

    gui_hooks.editor_did_init_buttons.append(_on_init_buttons)
    gui_hooks.editor_did_load_note.append(_on_load_note)
