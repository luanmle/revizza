# Research: Scheduler de Deleção de Contas (LGPD)

## Decision: Mecanismo de agendamento — Heroku Scheduler

**Decision**: Usar o add-on **Heroku Scheduler** para disparar
`python manage.py delete_expired_accounts` uma vez por dia.

**Rationale**: O add-on é gratuito, já roda sobre o dyno existente (mesmo
`DATABASE_URL`/config vars do `web`), e não exige nenhuma dependência Python
nova (sem APScheduler/Celery). Cumpre FR-001 (execução automática, sem
disparo manual) com o menor acréscimo de complexidade possível — alinhado a
Principle V (YAGNI) e Principle VI (ponytail) da constituição.

**Alternatives considered**:
- **`clock` dyno com APScheduler ou Celery beat**: dá mais controle de
  cadência (ex.: de hora em hora) e roda um processo de longa duração, mas
  custa um dyno adicional 24/7 e introduz uma dependência nova só para
  disparar um comando uma vez por dia — rejeitado por YAGNI: a carência de
  7 dias tem folga de sobra para uma checagem diária.
- **GitHub Actions com cron `schedule:` chamando um endpoint de management
  autenticado**: exigiria expor um endpoint HTTP novo só para isso,
  violando Principle IV (superfície nova desnecessária) sem necessidade,
  já que o Heroku Scheduler já roda o comando diretamente no dyno.

## Decision: Isolamento de falha por conta

**Decision**: Envolver a chamada a `supabase_gateway.delete_user` (dentro do
`with transaction.atomic()` por usuário, em `jobs.py`) em um `try/except`
que loga o erro e continua o loop, em vez de deixar a exceção propagar e
abortar o restante do lote.

**Rationale**: Hoje uma falha na primeira conta do lote (ex.: erro
transitório na API do Supabase Auth) propaga para fora do `for`, abortando
a exclusão de todas as contas subsequentes no mesmo ciclo — viola FR-005.
Como o `transaction.atomic()` já garante que a conta com falha não é
alterada (rollback), basta capturar a exceção *fora* do bloco atômico (ou
delimitando-a de forma que o rollback aconteça antes do `except`) para que
o loop continue para as próximas contas, e a conta com falha permaneça
elegível (mesmo filtro `deletion_requested_at__lte=cutoff`) para o próximo
ciclo — cumprindo FR-006 sem lógica de retry própria (o próprio agendamento
diário já é o mecanismo de retry).

**Alternatives considered**:
- **Fila de retry dedicada (ex.: nova tabela `DeletionFailure` ou tarefa
  assíncrona)**: rejeitado por YAGNI — o próprio filtro de elegibilidade já
  torna a conta "candidata de novo" no próximo ciclo diário, sem estado
  extra.

## Decision: Registro auditável (FR-007/FR-008)

**Decision**: Usar `logging` (stdlib, já configurado via Django) para emitir
uma linha estruturada por execução — quantidade de sucessos, quantidade de
falhas e timestamp — no `management command`, sem criar tabela nova no
banco.

**Rationale**: O Heroku já captura e retém a saída de log de cada execução
do Scheduler (visível via `heroku logs` e qualquer log drain configurado,
ex. Sentry/Papertrail). Isso satisfaz "registro auditável e consultável"
sem adicionar uma tabela cujo único propósito seria duplicar o que o log já
oferece — alinhado a Principle V/VI.

**Alternatives considered**:
- **Tabela `AccountDeletionRun` persistida no Postgres**: daria consulta
  via SQL/admin e retenção independente do provedor de log, mas é
  infraestrutura nova para um requisito que o logging padrão já atende no
  estágio atual (MVP, sem SLA de retenção de auditoria definido). Revisitar
  se compliance exigir consulta histórica além da retenção de log do
  provedor.
