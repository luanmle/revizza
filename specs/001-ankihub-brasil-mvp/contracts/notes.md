# Contract: Notes & General Discussion (US-03, US-04)

Ver convenções gerais em `api-conventions.md`.

| Método | Rota | Auth | Descrição | Requisito |
|---|---|---|---|---|
| GET | `/api/v1/decks/{id}/notes/` | usuário (assinante) | Busca por termo textual (`?q=`) ou ID exato (`?note_id=`); resposta em <500ms para decks de até 10 mil notas | FR-010 |
| GET | `/api/v1/notes/{id}/` | usuário (assinante do deck) | Detalhe da nota: `field_values` (HTML sanitizado) + `note_type.templates`/`note_type.css`, o suficiente para o frontend montar o preview isolado (`iframe sandbox srcDoc`, research.md #13) sem depender do design system | FR-011 |
| GET | `/api/v1/notes/{id}/comments/` | usuário (assinante) | Lista cronológica da thread geral da nota | FR-012 |
| POST | `/api/v1/notes/{id}/comments/` | usuário (assinante) | Cria comentário na thread geral | FR-012 |
| PATCH | `/api/v1/comments/{id}/` | autor do comentário | Edita o próprio comentário | FR-012 |
| DELETE | `/api/v1/comments/{id}/` | autor do comentário | Exclui o próprio comentário | FR-012 |
| POST | `/api/v1/comments/{id}/reports/` | usuário | Denuncia o comentário (motivo opcional) | FR-048 |
