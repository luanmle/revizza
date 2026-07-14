# Contract Delta: Suggestions API — múltiplos tipos de nota

Ver contrato base em `specs/001-ankihub-brasil-mvp/contracts/suggestions.md`. Só as mudanças abaixo se
aplicam.

## `POST /api/v1/notes/{id}/suggestions/change/` e `POST /api/v1/suggestions/bulk-change/`

**Sem mudança de payload de entrada.** Muda a validação de `proposed_field_values`: os nomes de campo
propostos são validados contra o `note_type.field_names` da(s) nota(s)-alvo, não mais contra um
`deck.note_type` único.

**Novo erro de negócio** (`bulk-change` apenas): `400` se as notas em `note_ids` não pertencerem todas
ao mesmo `NoteType` — `{"errors": {"note_ids": ["Todas as notas devem ser do mesmo tipo de nota."]}}`.

## `POST /api/v1/decks/{id}/suggestions/new-note/`

**Novo campo obrigatório no corpo**: `note_type_id` (UUID) — deve ser um dos tipos de nota já
presentes no deck no momento da sugestão. `400` se ausente ou se não pertencer ao deck. Os campos de
`proposed_field_values` são validados contra o `field_names` desse `note_type_id` (antes: contra
`deck.note_type.field_names`).

**Resposta**: inclui `note_type_id` no corpo (antes ausente, pois era implícito).

## `POST /api/v1/suggestions/{id}/accept/`

**Sem mudança de rota/payload.** Para sugestões `type=new_note`, a nota criada usa
`suggestion.note_type` (o tipo escolhido na criação) em vez de `suggestion.deck.note_type` (que deixou
de existir).
