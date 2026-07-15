"""Ações de nota na barra inferior do revisor (contracts/addon-actions.md).

Botões "Ver no Revizza" (US1) e "Ver histórico" (US3) — só aparecem quando o
GUID da nota atual está no cache de sync (regra de visibilidade, FR-001).

`aqt` é importado dentro das funções: os testes headless importam o módulo sem
um Anki gráfico rodando.

ponytail: a barra inferior do revisor não tem hook de "adicionar botão"; injeção
via JS eval em `mw.reviewer.bottom.web` é a mesma técnica do add-on real do
AnkiHub. Teto: se o Anki mudar o markup, ajustar só o JS abaixo.
"""

from ..db.models import deck_id_for_guid
from ..main.constants import connection_settings

# JS isolado (teto do ponytail): remove botões antigos e reinjeta um par.
_INJECT_JS = """(function(){
  function mk(id, label, title, cmd){
    var old = document.getElementById(id);
    if (old) old.remove();
    var b = document.createElement('button');
    b.id = id;
    b.title = title;
    b.textContent = label;
    b.onclick = function(){ pycmd(cmd); };
    document.body.appendChild(b);
  }
  mk('revizza-view-btn', 'Ver no Revizza', 'Abrir esta nota no Revizza', 'revizza:view');
  mk('revizza-history-btn', 'Ver histórico', 'Ver histórico de sugestões desta nota', 'revizza:history');
})();"""


def _guid_of_card(card) -> str | None:
    """GUID da nota do card atual, ou None se indisponível."""
    if card is None:
        return None
    return card.note().guid


def is_action_visible(card) -> bool:
    """Regra de visibilidade: nota do card pertence a um deck Revizza inscrito."""
    guid = _guid_of_card(card)
    return bool(guid) and deck_id_for_guid(guid) is not None


def _api_base() -> str:
    from aqt import mw

    return connection_settings(mw.addonManager.getConfig("ankihub_br") or {})[
        "api_base_url"
    ]


def _on_reviewer_shown(card) -> None:
    from aqt import mw

    if is_action_visible(card):
        mw.reviewer.bottom.web.eval(_INJECT_JS)


def _open_view() -> None:
    from aqt import mw
    from aqt.utils import openLink

    guid = _guid_of_card(mw.reviewer.card)
    if guid:
        openLink(f"{_api_base()}/go/note/{guid}/")


def _open_history() -> None:
    from aqt import mw
    from aqt.utils import openLink

    guid = _guid_of_card(mw.reviewer.card)
    if guid:
        openLink(f"{_api_base()}/go/note/{guid}/history/")


def _on_js_message(handled, message, context):
    if message == "revizza:view":
        _open_view()
        return (True, None)
    if message == "revizza:history":
        _open_history()
        return (True, None)
    return handled


def setup() -> None:
    from aqt import gui_hooks

    gui_hooks.reviewer_did_show_question.append(_on_reviewer_shown)
    gui_hooks.reviewer_did_show_answer.append(_on_reviewer_shown)
    gui_hooks.webview_did_receive_js_message.append(_on_js_message)
