# Bug Assessment: publish 400 — add-on multi-notetype vs backend em produção

- **Slug**: publish-400
- **Created**: 2026-07-14
- **Source**: pasted text
- **Verdict**: valid
- **Severity**: high

## Report (verbatim or summarized)

> A importação falhou: 400 Client Error: Bad Request for url:
> https://revizza-api-37fd874aff98.herokuapp.com/api/v1/decks/4da26dfa-80cc-417e-8aab-2b589f6395ba/publish/
> ao tentar sincronizar

## Symptom

Publicação inicial de um deck via add-on falha com `400 Bad Request` no endpoint
`/decks/{id}/publish/`. Esperado: publicação aceita (deck criado no catálogo). O `id` na URL é
gerado pelo add-on no primeiro publish (create-only), então não é republicação.

## Reproduction

1. Rodar o add-on **com o código da branch `002-multi-notetype-decks`** (que monta
   `note_types: [...]`).
2. Apontar para a API em produção (Heroku, `revizza-api-...herokuapp.com`), que roda o código da
   `main` (pré-002).
3. Publicar qualquer deck (mesmo de tipo único).
4. Backend responde `400 {"detail": "Payload requer name e note_type.field_names."}`.

## Suspected Code Paths

- `addon/ankihub_br/main/publish.py:79-88` (branch 002) — payload usa chave **`note_types`** (lista),
  sem `note_type` singular.
- `backend/apps/sync/views.py:240-243` (**`main` = deploy Heroku**) — `PublishView.post` lê
  `data.get("note_type")` (objeto único); com o novo payload isso vira `{}`, `field_names` ausente,
  retorna `400 "Payload requer name e note_type.field_names."`.
- `backend/apps/sync/views.py:258-267` (branch 002, ainda não deployado) — versão nova já lê
  `data.get("note_types")` corretamente.

## Root Cause Hypothesis

**Version skew de release**, não defeito de lógica. Confiança: **alta**.

O add-on foi atualizado para o contrato multi-notetype (`note_types: list`) pela feature
`002-multi-notetype-decks`, mas essa feature vive só na branch `git branch --contains HEAD` →
`002-multi-notetype-decks` e **não foi merjada na `main` nem deployada no Heroku**. A API em produção
ainda espera `note_type` (objeto único). Add-on novo + backend velho = `400` em todo publish,
inclusive de decks de tipo único. A mensagem exata de erro da `main`
(`"Payload requer name e note_type.field_names."`) confirma o caminho.

## Proposed Remediation

**Preferred**: Não há correção de código a fazer — o código correto já existe na branch
`002-multi-notetype-decks`. Remediação = **release**: merjar `002-multi-notetype-decks` na `main`
(migrações `catalog/0004_remove_deck_note_type`, `suggestions/0005_suggestion_note_type` incluídas) e
deployar no Heroku, rodando `python manage.py migrate` no deploy. Após o deploy, o backend passa a
aceitar `note_types[]` e o publish volta a funcionar para decks de tipo único e misto.

**Alternatives**:
- Fazer o add-on enviar os dois formatos (`note_type` + `note_types`) para compatibilizar com o backend
  antigo. **Trade-off**: adiciona código de compatibilidade descartável para um backend que vai ser
  substituído no próximo deploy — dívida sem ganho (viola YAGNI). Não recomendado.

**Files likely to change**: nenhum arquivo de código-fonte. Ação é de deploy/release. Se for necessário
provar a compatibilidade de versão automaticamente, considerar:
- `backend/tests/contract/test_sync_publish.py` — já cobre o novo contrato na branch 002.

**Tests to add or update**:
- Nenhum novo teste de código exigido; a suíte da branch 002 (`test_sync_publish.py`) já valida o
  contrato correto. O gap é operacional (deploy), não de cobertura.

## Risks & Considerations

- **Migrações no deploy**: o merge traz uma migração destrutiva (`remove_deck_note_type`). Rodar
  `migrate` no release do Heroku; conferir que nenhum deck em produção dependa da FK removida (é
  aditiva/derivada por design — ver `research.md` Decisão 1).
- **Ordem de release**: idealmente backend deploya **antes ou junto** com a distribuição do add-on novo
  aos usuários. Se add-on novo já está na mão de usuários, todo publish está quebrado até o deploy —
  daí severity `high`.
- **Compatibilidade retroativa**: SC-003 — decks de tipo único continuam publicando após o deploy
  (payload de 1 item em `note_types`).

## Open Questions

- [NEEDS CLARIFICATION: confirmar que o Heroku (`revizza-api-...`) deploya a partir da branch `main` e
  que `002-multi-notetype-decks` ainda não foi merjada lá — assumido pelo estado local do git.]
