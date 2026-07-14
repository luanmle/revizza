# Contract: Suggestions & Community Moderation (US-05, US-06, US-07, US-09, US-10)

Ver convenções gerais em `api-conventions.md`.

| Método | Rota | Auth | Descrição | Requisito |
|---|---|---|---|---|
| POST | `/api/v1/notes/{id}/suggestions/change/` | usuário (assinante) | Cria sugestão de mudança: `change_category`, `justification`, `proposed_field_values` (HTML sanitizado no backend) | FR-013, FR-014, FR-015, FR-016 |
| POST | `/api/v1/suggestions/bulk-change/` | usuário (assinante) | Sugestão de mudança aplicada a várias notas de uma vez (`note_ids: [...]`) — cria uma única `Suggestion` | FR-017 |
| POST | `/api/v1/decks/{id}/suggestions/new-note/` | usuário (assinante) | Propõe nota nova: campos do tipo de nota do deck, `justification`, `tags` | FR-018 |
| POST | `/api/v1/notes/{id}/suggestions/deletion/` | usuário (assinante) | Sugere exclusão da nota, `justification` obrigatória | FR-019 |
| GET | `/api/v1/decks/{id}/suggestions/` | usuário (assinante) | Lista sugestões do deck; `?type=change\|new_note\|deletion`, `?status=`, `?author=`, `?note_id=`, `?created_after=`/`created_before=`, `?submission=individual\|bulk` | FR-021, FR-022 |
| GET | `/api/v1/suggestions/{id}/` | usuário (assinante do deck) | Detalhe: `author_name`, data, tipo, justificativa, diff/campos propostos, contexto atual das notas-alvo com contagem de sugestões abertas, curtidas | FR-020 |
| POST | `/api/v1/suggestions/{id}/votes/` | usuário (assinante) | `{"value": "like"\|"dislike"}`; idempotente (upsert por usuário) | FR-023 |
| DELETE | `/api/v1/suggestions/{id}/votes/me/` | usuário (assinante) | Remove o próprio voto | FR-023 |
| GET | `/api/v1/suggestions/{id}/comments/` | usuário (assinante) | Thread de discussão da sugestão (distinta da thread geral da nota) | FR-024 |
| POST | `/api/v1/suggestions/{id}/comments/` | usuário (assinante) | Comenta na thread da sugestão | FR-024 |
| POST | `/api/v1/suggestion-comments/{id}/reports/` | usuário | Denuncia mensagem da thread de sugestão | FR-048 |
| POST | `/api/v1/suggestions/{id}/accept/` | moderador do deck | Aplica a mudança na nota oficial (cria/atualiza/remove conforme o tipo), marca `accepted`, enfileira para sincronização | FR-025, FR-026 |
| POST | `/api/v1/suggestions/{id}/reject/` | moderador do deck | Marca `rejected`, `rejection_reason` opcional visível ao autor | FR-025, FR-027 |

**Erros de negócio notáveis**:
- `409` ao tentar `accept`/`reject` uma sugestão que não está `pending` (decisão é terminal, FR-027).
- `403` em `accept`/`reject` para quem não é moderador ativo do deck.
