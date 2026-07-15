"""Bucket público `avatars` no Supabase Storage (007, research.md).

Idempotente: cria o bucket se não existir e garante que é público (avatares saem por
URL pública direta, sem assinatura — ao contrário do bucket `media`).
"""

from django.core.management.base import BaseCommand

from apps.accounts import avatars


class Command(BaseCommand):
    help = "Cria/garante o bucket público 'avatars' no Supabase Storage."

    def handle(self, *args, **options):
        storage = avatars._storage()
        existing = {bucket.id: bucket for bucket in storage.list_buckets()}

        if avatars.BUCKET not in existing:
            storage.create_bucket(avatars.BUCKET, options={"public": True})
            self.stdout.write(
                self.style.SUCCESS(f"Bucket '{avatars.BUCKET}' criado (público).")
            )
        elif not existing[avatars.BUCKET].public:
            storage.update_bucket(avatars.BUCKET, options={"public": True})
            self.stdout.write(f"Bucket '{avatars.BUCKET}' era privado; agora é público.")
        else:
            self.stdout.write(f"Bucket '{avatars.BUCKET}' já existe e é público.")
