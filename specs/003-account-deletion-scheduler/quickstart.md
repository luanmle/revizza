# Quickstart: Scheduler de Deleção de Contas (LGPD)

## Pré-requisitos

- App Heroku já existente (backend deployado, ver CLAUDE.md → hosting).
- Acesso `heroku` CLI autenticado no app, ou acesso ao dashboard.

## Provisionar o agendamento (produção)

```bash
heroku addons:create scheduler:standard -a <app-name>
heroku addons:open scheduler -a <app-name>
```

No dashboard do Scheduler, adicionar um job:

- **Command**: `python manage.py delete_expired_accounts`
- **Frequency**: Daily
- **Next due at**: qualquer horário de baixo tráfego (ex.: 03:00 UTC)

## Validar localmente (sem depender do Heroku)

1. Criar uma conta de teste com `deletion_requested_at` há mais de 7 dias:

   ```python
   from django.utils import timezone
   from datetime import timedelta
   from apps.accounts.models import User

   u = User.objects.create(..., deletion_requested_at=timezone.now() - timedelta(days=8))
   ```

2. Rodar o comando manualmente e conferir o log estruturado e a exclusão:

   ```bash
   python manage.py delete_expired_accounts
   ```

   Saída esperada: linha de log com contagem de sucesso/falha e timestamp;
   `User.objects.filter(pk=u.pk).exists()` deve ser `False`.

3. Rodar o comando **duas vezes seguidas** (idempotência, FR-004): a segunda
   execução não deve gerar erro nem tentar excluir a mesma conta de novo.

4. Simular falha isolada (US2/FR-005, FR-006): mockar
   `supabase_gateway.delete_user` para levantar exceção em uma conta entre
   várias elegíveis; confirmar que as demais são excluídas no mesmo run, e
   que a conta com falha continua elegível (não excluída) para o próximo
   run — ver `backend/apps/accounts/tests/test_jobs.py`.

## Referências

- Lógica de negócio: [data-model.md](./data-model.md)
- Decisões de mecanismo (Heroku Scheduler, isolamento de falha, logging):
  [research.md](./research.md)
