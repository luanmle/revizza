# Contract: Add-on Sync API (US-08)

Ver convenções gerais em `api-conventions.md`. Estas rotas são consumidas exclusivamente pelo add-on
Anki — nunca diretamente pelo frontend web.

| Método | Rota | Auth | Descrição | Requisito |
|---|---|---|---|---|
| POST | `/api/v1/decks/{id}/publish/` | criador autenticado | Importação inicial única (tipos de nota, notas, mídia) — cria o primeiro snapshot oficial; responde `409` se o deck já existir e nunca republica conteúdo local | PRD §4.1, Constituição II |
| GET | `/api/v1/decks/{id}/sync/delta/` | assinante | Retorna o delta desde `?since_mod=<timestamp>`, na ordem tipos de nota → notas → subdecks; inclui `full_resync_required: bool` quando a mudança estrutural não é reconciliável via delta parcial | FR-031, FR-034, FR-035 |
| GET | `/api/v1/decks/{id}/sync/full/` | assinante | Retorna o deck completo (tipos de nota, notas, tags, subdecks) para ressincronização total | FR-035 |
| GET | `/api/v1/media/{content_hash}/` | assinante | Retorna URL pré-assinada do Supabase Storage para a mídia, apenas se o hash não corresponde ao já presente localmente | FR-036 |

**Regras aplicadas neste conjunto de rotas**:
- Publicação: o `POST .../publish/` é create-only. Depois da importação inicial, mudanças oficiais
  entram pela web e pelo fluxo de sugestão → moderação; o add-on nunca sobrescreve o deck oficial.
- Rate limit: no máximo uma requisição de sincronização (`delta`/`full`) por usuário a cada 10
  segundos; excesso responde `429` (FR-032, FR-052).
- Compatibilidade: o add-on só é suportado rodando na versão LTS mais recente do Anki Desktop —
  a API não versiona por cliente, mas o add-on reporta sua versão do Anki no header
  `X-Anki-Version` para telemetria/diagnóstico (FR-038).
- Falha/interrupção: é responsabilidade do **add-on** (não da API) reverter a coleção local para o
  backup pré-sync e reexecutar do zero caso a aplicação do delta seja interrompida — a API apenas
  garante que `delta`/`full` são idempotentes e seguros para reexecutar (FR-039, FR-033).
- Preferência de remoção: o campo `delete_notes_on_removal` da assinatura (ver `catalog.md`)
  determina se o add-on apaga a nota de fato ou apenas a marca ao aplicar uma remoção vinda do
  delta (FR-037).
- Proteção: antes de aplicar qualquer valor de campo/tag do delta, o add-on consulta
  `GET /decks/{id}/protection/me/` (ver `protection.md`) e preserva o que estiver protegido — por
  configuração de deck ou por tag `AnkiHubBR_Protect::<Campo>` já presente na nota local — assim
  como nunca toca tags internas de outros add-ons (ex. `leech`, `marked`) (FR-040 a FR-044).
- Compatibilidade retroativa: como o Anki não força atualização imediata do add-on, este conjunto de
  rotas deve continuar servindo a versão de contrato anterior por um período de transição sempre que
  uma mudança breaking for publicada (versionamento via header `Accept`, ver `api-conventions.md`) —
  risco de "fragmentação de versões do add-on" citado no PRD §5.2.
- URL do backend: configurável na tela de preferências do add-on (`config.json`), nunca hardcoded —
  permite apontar o mesmo add-on para staging/produção sem rebuild (PRD §4.6).
