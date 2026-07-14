"""T137: bucket privado `media` no Supabase Storage (FR-036).

Idempotente: cria o bucket se não existir e garante que é privado (mídia só sai
por URL pré-assinada). `--verify` faz um round-trip real de upload/download com
as mesmas URLs assinadas que o backend entrega ao add-on.
"""

import urllib.request
import uuid

from django.core.management.base import BaseCommand, CommandError

from apps.sync import media


class Command(BaseCommand):
    help = "Cria/garante o bucket privado 'media' no Supabase Storage (T137)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Faz upload+download reais via URLs pré-assinadas do backend.",
        )

    def handle(self, *args, **options):
        storage = media._storage()
        existing = {bucket.id: bucket for bucket in storage.list_buckets()}

        if media.BUCKET not in existing:
            storage.create_bucket(media.BUCKET, options={"public": False})
            self.stdout.write(
                self.style.SUCCESS(f"Bucket '{media.BUCKET}' criado (privado).")
            )
        elif existing[media.BUCKET].public:
            storage.update_bucket(media.BUCKET, options={"public": False})
            self.stdout.write(f"Bucket '{media.BUCKET}' era público; agora é privado.")
        else:
            self.stdout.write(f"Bucket '{media.BUCKET}' já existe e é privado.")

        if options["verify"]:
            self._verify(storage)

    def _verify(self, storage):
        path = f"_healthcheck/{uuid.uuid4().hex}"
        payload = b"ankihub-brasil-media-check"
        try:
            upload = urllib.request.Request(
                media.signed_upload_url(path), data=payload, method="PUT"
            )
            with urllib.request.urlopen(upload) as response:
                if response.status not in (200, 201):
                    raise CommandError(
                        f"Upload assinado falhou: HTTP {response.status}"
                    )
            with urllib.request.urlopen(media.signed_download_url(path)) as response:
                if response.read() != payload:
                    raise CommandError("Download assinado devolveu conteúdo diferente.")
        finally:
            storage.from_(media.BUCKET).remove([path])
        self.stdout.write(self.style.SUCCESS("URLs assinadas de upload/download OK."))
