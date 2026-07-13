# API Conventions (aplicam-se a todos os contratos neste diretório)

Referência: PRD §4.2, research.md §3 (Princípio I da Constituição — Parity Over Reinvention).

- **Base path**: `/api/v1/...` — todas as rotas terminam com barra final (`/decks/`, não `/decks`).
- **Versionamento**: via header `Accept` (ex.: `Accept: application/json; version=1`), não via path.
  Quando uma mudança breaking for necessária, o backend mantém a versão de contrato anterior
  disponível por um período de transição — o AnkiWeb não força atualização imediata do add-on
  instalado, então múltiplas versões do cliente convivem em produção (PRD §4.6, §5.2; ver
  `sync.md`).
- **Autenticação**: header `Authorization: Bearer <token>` emitido pelo Supabase Auth. Endpoints
  marcados "público" abaixo não exigem autenticação; todos os demais exigem.
- **Paginação**: cursor-based em toda listagem (`?cursor=...`), resposta no formato:
  ```json
  { "next": "https://.../recurso/?cursor=abc123", "previous": null, "results": [ ... ] }
  ```
- **Erros**: corpo `{ "detail": "mensagem legível" }` para erros de um único motivo; `{ "errors": {"campo": ["mensagem"]} }` para erros de validação por campo. Códigos HTTP padrão (400/401/403/404/409/429).
- **Rate limiting**: endpoints de sincronização e de submissão de sugestão respondem `429` com
  header `Retry-After` quando o limite é excedido (FR-032, FR-052).
- **Formato de data/hora**: ISO 8601 UTC em toda a API.
- **Idempotência de sugestão em lote**: `bulk-change` aceita uma lista de IDs de nota; a resposta
  contém uma única `Suggestion` vinculada a todas elas (FR-017).
