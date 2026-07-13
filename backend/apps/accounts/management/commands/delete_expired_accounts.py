from django.core.management.base import BaseCommand

from apps.accounts.jobs import delete_expired_accounts


class Command(BaseCommand):
    help = "Exclui contas após a carência LGPD de 7 dias."

    def handle(self, *args, **options):
        deleted = delete_expired_accounts()
        self.stdout.write(f"{deleted} conta(s) excluída(s).")
