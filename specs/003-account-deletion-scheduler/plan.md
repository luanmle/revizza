# Implementation Plan: Scheduler de Deleção de Contas (LGPD)

**Branch**: `003-account-deletion-scheduler` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-account-deletion-scheduler/spec.md`

## Summary

`delete_expired_accounts` (backend/apps/accounts/jobs.py) e seu management
command já implementam a exclusão de contas vencidas, mas nada os dispara em
produção. O plano é: (1) provisionar o **Heroku Scheduler** (add-on gratuito)
para rodar `python manage.py delete_expired_accounts` diariamente; (2)
corrigir `jobs.py` para isolar a falha de uma conta (try/except por
iteração) sem abortar o restante do lote, mantendo a conta falha elegível
para retry no próximo ciclo; (3) fazer o command emitir um log estruturado
(contagem de sucesso/falha + timestamp) via `logging`, que o Heroku já
captura nos logs do dyno — sem introduzir uma tabela de auditoria nova.

## Technical Context

**Language/Version**: Python 3.12 (já em uso no backend, ver `.venv`)

**Primary Dependencies**: Django + DRF (já instalados); nenhuma dependência
nova — `logging` é stdlib, o agendamento é um add-on de infraestrutura
(Heroku Scheduler), não uma lib Python.

**Storage**: Postgres via Supabase (mesmo `User` model já existente); nenhuma
tabela nova.

**Testing**: pytest (padrão já usado em `backend/tests/unit|contract|integration/`).

**Target Platform**: Heroku (dyno one-off disparado pelo Heroku Scheduler),
mesmo app já hospedado no `web` do Procfile.

**Project Type**: web-service (backend Django existente) — sem frontend/add-on
envolvidos nesta feature.

**Performance Goals**: N/A — job em lote, baixo volume esperado (dezenas a
centenas de contas por ciclo), sem requisito de latência.

**Constraints**: sem custo adicional de infraestrutura (Heroku Scheduler é
gratuito); execução idempotente e segura mesmo se disparada mais de uma vez
no mesmo dia.

**Scale/Scope**: número de contas com `deletion_requested_at` vencido em um
dado ciclo; não crítico em performance.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle III (LGPD by design)** — aplicável e é a motivação central da
  feature: fecha o gap entre "carência de 7 dias declarada" e "carência de 7
  dias efetivamente cumprida". Não altera consentimento nem exportação
  (fora de escopo). **PASS**.
- **Principle V (YAGNI / preferir serviço gerenciado)** — Heroku Scheduler
  (add-on gratuito, já disponível na plataforma de hosting ratificada) é
  escolhido sobre um `clock` dyno com APScheduler/Celery beat: mesma
  cadência diária, zero dependência nova, zero dyno extra pago. Log
  estruturado via `logging` stdlib é escolhido sobre uma tabela de
  auditoria nova pelo mesmo motivo (o Heroku já persiste/captura logs do
  dyno). **PASS**.
- **Principle IV (Secure by default)** — não introduz endpoint novo nem
  superfície HTTP nova; a chamada a `supabase_gateway.delete_user` já existe
  e já usa HTTPS. **PASS (não aplicável na maior parte)**.
- **Principles I, II, VI, VII, VIII** — não aplicáveis: feature não toca
  sync, notas/decks, UI, nem convenções de API do AnkiHub.

## Project Structure

### Documentation (this feature)

```text
specs/003-account-deletion-scheduler/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory: this feature adds no new API surface (no new
endpoint, no new external interface) — it schedules and hardens an existing
internal management command.

### Source Code (repository root)

```text
backend/
├── apps/accounts/
│   ├── jobs.py                                    # MODIFY: isolate per-account failure (try/except), structured log line
│   └── management/commands/delete_expired_accounts.py  # MODIFY: log structured summary (deleted/failed counts, timestamp)
├── tests/unit/
│   └── test_delete_expired_accounts.py            # MODIFY/ADD: cases for partial failure isolation + retry
├── Procfile                                       # unchanged (no new dyno process — Heroku Scheduler calls the existing one-off command)
```

**Structure Decision**: Single existing project (`backend/`, Django). This
feature only touches the `accounts` app already responsible for the
deletion logic — no new app, no new project, no frontend/add-on change.
Scheduling itself lives outside the repo (Heroku Scheduler add-on
configuration in the Heroku dashboard/CLI, documented in `quickstart.md`),
not as a new `Procfile` process, since the add-on invokes `manage.py`
directly on its own cadence.

## Complexity Tracking

No constitution violations. Not applicable.
