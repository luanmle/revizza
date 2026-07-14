# Contract Delta: Catalog API — múltiplos tipos de nota

Ver contrato base em `specs/001-ankihub-brasil-mvp/contracts/catalog.md`. Sem mudança de rota.

## `GET /api/v1/decks/{id}/`

`note_type` (objeto único `{id, name, field_names}`) é substituído por `note_types` (lista de
`{id, name, field_names, note_count}`, uma entrada por tipo de nota distinto presente no deck) —
atende FR-009/US3. Decks publicados antes desta feature continuam retornando uma lista com um único
item, forma equivalente ao objeto único anterior.
