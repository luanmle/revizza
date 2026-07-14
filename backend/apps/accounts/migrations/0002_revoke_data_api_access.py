"""T127: isola as tabelas do Django da Data API do Supabase (Constitution III/IV).

Revoga todo acesso dos roles `anon`/`authenticated` às tabelas do schema `public`
(existentes e futuras, via default privileges) e liga RLS como defesa em profundidade.
O Django conecta como dono das tabelas (role `postgres`), que não é afetado por RLS
não-forçada nem pelos revokes. No-op fora do Postgres (sqlite de dev/teste).
"""

from django.db import migrations

REVOKE_SQL = """
DO $$
DECLARE
    t text;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('anon', 'authenticated')) THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
        REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON TABLES FROM anon, authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON SEQUENCES FROM anon, authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON FUNCTIONS FROM anon, authenticated;
    END IF;
    FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    END LOOP;
END $$;
"""


def revoke_data_api_access(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(REVOKE_SQL)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    # sem reverso: reexpor tabelas do Django à Data API nunca é desejado
    operations = [
        migrations.RunPython(revoke_data_api_access, migrations.RunPython.noop)
    ]
