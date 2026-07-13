# Contract: Catalog & Subscriptions (US-02, US-08 parte web)

Ver convenções gerais em `api-conventions.md`.

| Método | Rota | Auth | Descrição | Requisito |
|---|---|---|---|---|
| GET | `/api/v1/decks/` | usuário | Lista paginada; `?tag=` para filtro; ordena por recomendação (carreira/banca do usuário) quando aplicável, senão por assinantes/recência | FR-006, FR-007, FR-008 |
| GET | `/api/v1/decks/{id}/` | usuário | Detalhe de um deck (nome, tags, contagem de notas/assinantes, moderadores) | FR-006 |
| POST | `/api/v1/decks/{id}/subscriptions/` | usuário | Cria assinatura (vínculo usuário↔deck); corpo opcional define preferências de gatilho de sync | FR-009 |
| PATCH | `/api/v1/decks/{id}/subscriptions/me/` | usuário | Atualiza preferências de sincronização (manual/auto-abertura/encadeado) e preferência de remoção local | US-08 |
| DELETE | `/api/v1/decks/{id}/subscriptions/me/` | usuário | Cancela assinatura | FR-009 |
