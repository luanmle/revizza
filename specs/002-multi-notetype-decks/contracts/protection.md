# Contract Delta: Field/Tag Protection API — múltiplos tipos de nota

Ver contrato base em `specs/001-ankihub-brasil-mvp/contracts/protection.md`. Sem mudança de rota ou
payload.

## `PUT /api/v1/decks/{id}/protection/me/`

Muda apenas a validação de `fields`: nomes desconhecidos são rejeitados contra a **união** dos
`field_names` de todos os tipos de nota do deck (antes: contra `deck.note_type.field_names`, o único
tipo de nota que existia). Um nome de campo protegido continua se aplicando deck-wide, a qualquer nota
que tenha um campo com esse nome — não há conceito de proteção por tipo de nota.
