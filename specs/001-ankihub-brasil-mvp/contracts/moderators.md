# Contract: Deck Moderators (US-11)

Ver convenções gerais em `api-conventions.md`.

| Método | Rota | Auth | Descrição | Requisito |
|---|---|---|---|---|
| GET | `/api/v1/decks/{id}/moderators/` | usuário (assinante) | Lista moderadores ativos e convites pendentes do deck | FR-028 |
| POST | `/api/v1/decks/{id}/moderators/` | moderador do deck | Convida usuário por e-mail/username; cria `DeckModerator` em status `pending` | FR-028 |
| POST | `/api/v1/deck-moderator-invites/{id}/accept/` | usuário convidado | Aceita convite, status vira `active` | FR-028 |
| DELETE | `/api/v1/decks/{id}/moderators/{user_id}/` | moderador do deck | Remove outro moderador; bloqueado se o alvo for o único moderador `active` restante | FR-029, FR-030 |

**Erro de negócio notável**: `409` ao tentar remover o único moderador `active` restante do deck
(FR-030 — um deck nunca pode ficar sem moderador).
