# Backend Django + gunicorn. DB e auth são externos (Supabase) — nenhum serviço extra.
#
# Multi-stage por causa do Heroku Container Registry: ele ignora o Procfile e decide o processo
# pela tag da imagem (registry.heroku.com/<app>/<web|release>), então cada tipo precisa do seu
# próprio target buildável (docs/deploy.md). `web` fica por último de propósito — é o target padrão
# de `docker build .` sem --target, preservando o comportamento usado por docker-compose.yml.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Static do Django admin servido pelo whitenoise; base.py não exige env em import.
RUN DJANGO_SETTINGS_MODULE=config.settings.base python manage.py collectstatic --noinput

RUN useradd --create-home appuser && chown -R appuser:appuser /app
ENV DJANGO_SETTINGS_MODULE=config.settings.prod

# --- release: roda o release phase do Heroku (migrate/cache/isolation), nunca serve tráfego ---
FROM base AS release

# curl só para os logs em tempo real do `heroku container:release` (opcional, mas barato aqui).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

USER appuser
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py createcachetable && python manage.py check_data_api_isolation"]

# --- web: serve tráfego HTTP (gunicorn) ---
FROM base AS web

USER appuser
EXPOSE 8000
# $PORT vem do Heroku em runtime (dinâmico); shell form pra permitir a expansão da env var.
CMD ["sh", "-c", "gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --log-file -"]
