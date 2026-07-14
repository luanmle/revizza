# Contract Delta: Add-on Sync API — múltiplos tipos de nota

Ver contrato base em `specs/001-ankihub-brasil-mvp/contracts/sync.md`. Só as mudanças abaixo se
aplicam; todo o resto do contrato (rate limit, atomicidade, versionamento, proteção antes do delta)
permanece igual.

## `POST /api/v1/decks/{id}/publish/`

**Antes**: corpo tinha `note_type: {name, field_names, templates, css}` (objeto único) e cada item de
`notes` era implicitamente do único tipo de nota do deck.

**Depois**: corpo tem `note_types: [{name, field_names, templates, css}, ...]` (lista, 1 ou mais
itens) e cada item de `notes` ganha `note_type_index: int` (posição em `note_types`, 0-based). O
backend cria uma linha `NoteType` por item de `note_types`, na mesma transação atômica do publish, e
associa cada `Note` ao `NoteType` do seu `note_type_index`.

Validação: `note_type_index` fora do intervalo de `note_types` é erro `400`. Continua valendo: deck já
existente responde `409` (create-only, Constituição II); requer `name` e ao menos um item de
`note_types` com `field_names` não vazio.

## `GET /api/v1/decks/{id}/sync/delta/` e `GET /api/v1/decks/{id}/sync/full/`

**Sem mudança de forma** — já retornavam `note_types: list` + `note_type_id` por nota
(`backend/apps/sync/views.py:78-101`). Muda apenas o **conteúdo**: `note_types` agora pode conter mais
de um item quando o deck tem mais de um tipo de nota. `full_resync_required` (FR-035) passa a ser
avaliado por tipo de nota individual: verdadeiro se **qualquer** tipo de nota do deck teve
`structure_changed_at` depois de `since_mod`, não só o antigo tipo único do deck.

## Compatibilidade

Add-ons publicados antes desta feature enviam `note_type` (singular) — o backend responde `400`
("Payload requer name e note_types[]." ou similar) para esse formato antigo assim que o novo contrato
entrar em vigor, já que `publish` é usado uma única vez por deck (create-only) e não há período de uso
misto esperado dentro de uma mesma importação. O lado de **leitura** (`delta`/`full`) já era compatível
antes desta feature e continua sendo — nenhum add-on existente quebra ao **sincronizar** decks (mesmo
os publicados antes desta feature, que sempre tiveram exatamente um `NoteType`).
