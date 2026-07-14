# Data Model: Scheduler de Deleção de Contas (LGPD)

Nenhuma tabela nova. A feature reutiliza o modelo `User` existente
(`backend/apps/accounts/models.py`) e adiciona apenas comportamento em torno
dele.

## User (existente, sem alteração de schema)

- `deletion_requested_at` (datetime, nullable): quando a exclusão foi
  solicitada. Já existe; usado como está para calcular elegibilidade
  (`deletion_requested_at <= now - 7 dias`).
- `auth_id`: identificador usado para excluir o usuário no Supabase Auth via
  `supabase_gateway.delete_user`.
- `subscriptions` (relação existente): usada para decrementar
  `Deck.subscriber_count` ao excluir — comportamento já implementado, sem
  mudança.

## Run (conceitual — não persistido)

Representa uma execução do ciclo de exclusão. Não é uma tabela; é apenas a
estrutura da linha de log emitida pelo management command a cada execução:

- `timestamp`: momento da execução (implícito no log, via `logging`).
- `deleted_count` (int): quantas contas foram excluídas com sucesso.
- `failed_count` (int): quantas contas elegíveis falharam nesta execução
  (permanecem elegíveis para o próximo ciclo).

Ver decisão em [research.md](./research.md#decision-registro-auditável-fr-007fr-008)
sobre por que isso é um log estruturado, e não uma entidade persistida.
