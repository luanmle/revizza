# Contract: Personal Field/Tag Protection (US-12)

Ver convenções gerais em `api-conventions.md`. Consumido pela web (para configurar) e pelo add-on
(para consultar antes de aplicar um delta — ver `sync.md`).

| Método | Rota | Auth | Descrição | Requisito |
|---|---|---|---|---|
| GET | `/api/v1/decks/{id}/protection/me/` | usuário (assinante) | Lista campos/tags protegidos configurados pelo usuário para este deck | FR-040 |
| PUT | `/api/v1/decks/{id}/protection/me/` | usuário (assinante) | Substitui a lista de campos/tags protegidos (aplica-se a todas as notas do deck) | FR-040 |

Nota: a proteção pontual por nota via tag `AnkiHubBR_Protect::<Campo>` (FR-041) não tem endpoint
próprio — é lida pelo add-on diretamente da coleção local do Anki, nunca enviada ao backend.
