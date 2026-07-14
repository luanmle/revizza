"""T127: checagem de deploy — prova que a Data API do Supabase não contorna o Django.

Roda na release phase do Heroku (ver backend/Procfile) e falha o deploy se
`anon`/`authenticated` tiverem qualquer privilégio em tabelas do schema `public`.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

PRIVILEGE_LEAKS_SQL = """
SELECT t.tablename, r.rolname, p.privilege
FROM pg_tables t
CROSS JOIN (VALUES ('anon'), ('authenticated')) AS r(rolname)
CROSS JOIN (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE')) AS p(privilege)
WHERE t.schemaname = 'public'
  AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r.rolname)
  AND has_table_privilege(r.rolname, format('public.%I', t.tablename), p.privilege)
ORDER BY t.tablename, r.rolname, p.privilege
"""


class Command(BaseCommand):
    help = (
        "Falha se anon/authenticated tiverem privilégio em qualquer tabela do "
        "schema public (isolamento da Data API do Supabase, T127)."
    )

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stdout.write(
                "Banco não é Postgres; checagem de Data API não se aplica."
            )
            return
        with connection.cursor() as cursor:
            cursor.execute(PRIVILEGE_LEAKS_SQL)
            leaks = cursor.fetchall()
        if leaks:
            details = "; ".join(
                f"{table}: {role} tem {priv}" for table, role, priv in leaks
            )
            raise CommandError(
                f"Data API do Supabase pode contornar o Django — {details}. "
                "Rode as migrações (accounts 0002) ou revogue os grants."
            )
        self.stdout.write(
            self.style.SUCCESS(
                "OK: anon/authenticated sem privilégios nas tabelas do Django."
            )
        )
