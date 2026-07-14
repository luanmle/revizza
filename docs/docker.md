# Docker — backend + frontend

Containeriza os dois deploys web (Django e Next.js) para rodar localmente em modo
produção contra o Supabase real. Postgres, Auth e Storage são externos (Supabase) —
não há container de banco. O add-on **não** dockeriza: roda dentro do processo do
Anki Desktop e é distribuído como `.ankiaddon`.

> Dev diário continua nativo (`python manage.py runserver` + `npm run dev`), com
> hot-reload. Os containers servem para paridade de produção e portabilidade de
> hosting (Railway/Render/Fly.io aceitam esses Dockerfiles direto — ver
> `TODO(HOSTING_YEAR2)` na constituição).

## Arquivos

| Arquivo | Papel |
|---|---|
| `backend/Dockerfile` | `python:3.12-slim`, `collectstatic` no build, non-root, gunicorn na `:8000` |
| `backend/.dockerignore` | exclui venv, sqlite, tests, `.env` |
| `frontend/Dockerfile` | `node:22-alpine`, 3 estágios (deps → build → production), non-root, `node server.js` na `:3000` |
| `frontend/.dockerignore` | exclui `node_modules`, `.next`, tests, `.env` |
| `docker-compose.yml` | orquestra os dois serviços; env externo via Supabase |

## Pré-requisitos

- `backend/.env` preenchido (copie de `backend/.env.example`)
- `frontend/.env.local` preenchido (copie de `frontend/.env.local.example`)

## Subir

```bash
# build + up (o --env-file alimenta os build args NEXT_PUBLIC_* do frontend)
docker compose --env-file frontend/.env.local up --build

# primeira vez: migrations + tabela de cache (paridade com o release phase do Heroku)
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py createcachetable
```

- Backend: <http://localhost:8000> (API em `/api/v1/`, admin em `/admin/`)
- Frontend: <http://localhost:3000>

Derrubar: `docker compose down`.

## Decisões e porquês

### Backend

- **whitenoise + `STATIC_ROOT`** (`config/settings/base.py`): o único consumidor de
  static é o Django admin (moderação de denúncias, US13). Sem isso o admin ficaria
  sem CSS em container. Storage padrão, sem manifest/cache-busting (`ponytail:` —
  trocar por `CompressedManifestStaticFilesStorage` se virar gargalo).
- **`collectstatic` roda no build da imagem** com `config.settings.base`, que não
  exige env em import. Em runtime a imagem usa `config.settings.prod`.
- **Migrations não rodam no boot** — mesma separação do `release` phase do Heroku
  (`Procfile`). Rode manualmente (comando acima).
- **Compose local usa `config.settings.dev`**: `prod` força `SECURE_SSL_REDIRECT`
  e exige `DJANGO_ALLOWED_HOSTS`/CORS via env — sem proxy TLS local, quebraria.
  Em deploy real (com TLS terminado fora), use `DJANGO_SETTINGS_MODULE=config.settings.prod`.

### Frontend

- **`output: "standalone"`** (`next.config.ts`): o build gera `.next/standalone/`
  com `server.js` próprio e `node_modules` mínimos — a imagem final não carrega o
  `node_modules` completo. `public/` e `.next/static/` são copiados à mão no
  Dockerfile (comportamento documentado do standalone).
- **`turbopack.root: __dirname`**: o `package-lock.json` da **raiz do repo** (CLI
  do shadcn) faz o Next inferir a raiz errada e aninhar o output em
  `standalone/frontend/`. O `root` fixa o app neste diretório. Não remova o
  lockfile da raiz — é do tooling shadcn.
- **`NEXT_PUBLIC_*` são gravadas no bundle em _build_ time**, não em runtime. Por
  isso entram como `build args` no compose (via `--env-file frontend/.env.local`),
  não como `environment`. Mudou o valor → rebuild da imagem.
- **Node 22 LTS** na imagem (Next 16 exige ≥20.9; Node 20 é EOL desde abr/2026).
  `engines` no `package.json` documenta o mínimo.

## Troubleshooting

| Sintoma | Causa provável | Fix |
|---|---|---|
| Admin sem CSS | imagem antiga sem `collectstatic`/whitenoise | rebuild: `docker compose build backend` |
| Frontend com URL de API errada | `NEXT_PUBLIC_*` é build-time | corrija `frontend/.env.local` e rebuild |
| `standalone/frontend/` aninhado voltou | `turbopack.root` removido do `next.config.ts` | restaurar o `root` |
| 500 no backend logo ao subir | migrations pendentes | `docker compose run --rm backend python manage.py migrate` |
| Rate-limit não segura entre workers | settings dev usam cache locmem (por processo) | esperado no compose local; prod usa `DatabaseCache` (T144) |

> **Cuidado**: `docker compose config` imprime os valores resolvidos do `.env`
> (chaves Supabase, senha do banco) no terminal. Não cole esse output em issue,
> chat ou log público.
