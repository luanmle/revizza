from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import Notification

RETENTION_DAYS = 90


class Command(BaseCommand):
    help = "Exclui notificações lidas há mais de 90 dias (FR-010)."

    def handle(self, *args, **options):
        deleted, _ = Notification.objects.filter(
            read_at__lt=timezone.now() - timedelta(days=RETENTION_DAYS)
        ).delete()
        self.stdout.write(f"{deleted} notificação(ões) excluída(s).")
