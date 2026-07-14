import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.jobs import delete_expired_accounts

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Exclui contas após a carência LGPD de 7 dias."

    def handle(self, *args, **options):
        deleted = delete_expired_accounts()
        # Contagem de falhas já foi registrada por jobs.delete_expired_accounts;
        # este log marca a execução do comando em si (research.md § auditoria).
        logger.info(
            "delete_expired_accounts (comando) concluído: deleted=%d timestamp=%s",
            deleted,
            timezone.now().isoformat(),
        )
        self.stdout.write(f"{deleted} conta(s) excluída(s).")
