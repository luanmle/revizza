# Backend Django + gunicorn. DB e auth são externos (Supabase) — nenhum serviço extra.
FROM python:3.12-slim

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
USER appuser

ENV DJANGO_SETTINGS_MODULE=config.settings.prod
EXPOSE 8000

# Migrations não rodam no boot (paridade com o release phase do Heroku):
#   docker compose run --rm backend python manage.py migrate
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000", "--log-file", "-"]
