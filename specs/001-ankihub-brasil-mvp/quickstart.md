# Quickstart: Validando o MVP do AnkiHub Brasil ponta-a-ponta

Este guia assume que os três componentes (`backend/`, `frontend/`, `addon/`) já foram implementados
conforme `plan.md`, `data-model.md` e `contracts/`. Ele documenta como rodar cada peça localmente e
como validar os dois cenários P1 mais críticos do spec de ponta a ponta. Não repete os contratos de
API nem o modelo de dados — veja os arquivos correspondentes.

## Pré-requisitos

- Um projeto Supabase (Postgres + Auth + Storage) — pode ser um projeto de desenvolvimento próprio,
  não precisa ser o de produção (região US East definida na Constituição só é obrigatória em prod).
- Python 3.12, Node.js 20 LTS.
- Anki Desktop (versão LTS mais recente — FR-038) instalado localmente, com a pasta de add-ons
  acessível para carregar o add-on em modo desenvolvimento.

## Subindo o backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencher DATABASE_URL (connection string "Session pooler"/Supavisor do
                       # dashboard), SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY (secret key
                       # sb_secret_...); SUPABASE_JWT_SECRET só para tokens HS256 legados
python manage.py migrate
python manage.py runserver
```

Em produção (Heroku) o `backend/Procfile` define o dyno `web` (gunicorn) e a release phase
(`migrate` + `createcachetable` + `check_data_api_isolation`); a versão do Python vem de
`backend/.python-version`.

Validação rápida: `GET http://localhost:8000/api/v1/decks/` deve responder `200` com
`{"next": null, "previous": null, "results": []}` em um banco vazio (ver `contracts/api-conventions.md`).

## Subindo o frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # apontar NEXT_PUBLIC_API_URL para o backend local
npm run dev
```

Validação rápida: abrir `http://localhost:3000` em uma viewport de 360px (DevTools) e confirmar
ausência de rolagem horizontal em qualquer tela (FR-053); navegar um fluxo crítico (login →
catálogo) somente via teclado, sem mouse (FR-055).

## Carregando o add-on no Anki Desktop

```bash
cd addon
python build.py  # gera e valida dist/ankihub_br.ankiaddon com dependências vendorizadas
```

Instalar `dist/ankihub_br.ankiaddon` pelo gerenciador de add-ons do Anki Desktop, reabrir o Anki e
configurar a URL do backend local nas preferências do add-on.

## Cenário de validação 1 — Sync inicial (User Story 1, 2 e 3)

1. Cadastrar um usuário via `POST /api/v1/accounts/register/` (ou pela UI web).
2. Como criador autenticado, importar uma única vez um deck de teste via
   `POST /api/v1/decks/{id}/publish/` com pelo menos 1 tipo de nota e 2 notas. Confirmar que repetir
   a chamada para o mesmo ID responde `409`; mudanças posteriores passam pela web/sugestões.
3. Logar na web com o usuário estudante, abrir o catálogo (`/decks/`) e confirmar que o deck
   aparece com contagem de notas correta (FR-006).
4. Clicar em "Inscrever-se" — confirmar `201` em `POST /decks/{id}/subscriptions/` (FR-009).
5. No Anki Desktop, disparar a sincronização manual do add-on — confirmar que as 2 notas aparecem
   na coleção local, dentro de um deck com o nome esperado.
6. Tentar disparar uma segunda sincronização imediatamente — confirmar resposta `429` (rate limit
   de 10s, FR-032).

**Resultado esperado**: notas visíveis no Anki Desktop idênticas ao conteúdo publicado na web,
sem exigir intervenção manual além do clique de sincronizar.

## Cenário de validação 2 — Sugestão → moderação → propagação (User Story 4 e 5)

1. Com o usuário estudante já assinante (cenário 1), abrir uma nota na web e criar uma sugestão de
   mudança (`POST /notes/{id}/suggestions/change/`) com `change_category` e `justification`
   preenchidos (FR-013).
2. Abrir a tela de Community Suggestions do deck (`GET /decks/{id}/suggestions/?type=change`) e
   confirmar que a sugestão aparece com status `pending`, visível mesmo sem ser moderador (FR-021).
3. Curtir a sugestão com outro usuário assinante (`POST /suggestions/{id}/votes/`) e confirmar que
   o contador de curtidas muda (FR-023).
4. Como moderador, aceitar a sugestão (`POST /suggestions/{id}/accept/`) — confirmar que a nota
   oficial reflete o novo valor de campo e que a sugestão vira `accepted` (FR-026).
5. No Anki Desktop, disparar nova sincronização — confirmar que o campo alterado chega atualizado
   localmente, sem exigir ressincronização completa do deck (delta parcial, FR-034).

**Resultado esperado**: a mudança aceita na web aparece no Anki local do assinante na próxima
sincronização, sem que o usuário precise refazer a assinatura ou perder outras notas/anotações.

## Validação transversal — Isolamento do preview de nota (FR-011)

Ao abrir uma nota na web (busca de US6), inspecionar o preview via DevTools e confirmar que ele
é renderizado dentro de um `<iframe>` próprio — nenhuma classe/estilo do design system do
frontend (Tailwind/shadcn) aparece computada dentro do documento do iframe, e o CSS nativo do
Anki (`NoteType.css`) governa sozinho a aparência do template.

## Cenário de validação 3 — Proteção de conteúdo pessoal (User Story 11)

1. No Anki Desktop, adicionar a tag `AnkiHubBR_Protect::Notas_pessoais` a uma nota sincronizada e
   escrever algo no campo "Notas pessoais" (se o tipo de nota do deck de teste tiver esse campo).
2. Na web, aceitar uma sugestão que altera esse mesmo campo nessa nota.
3. Sincronizar novamente no Anki Desktop — confirmar que o conteúdo do campo protegido **não** foi
   sobrescrito, enquanto os demais campos da nota refletem a mudança aceita (FR-042).
