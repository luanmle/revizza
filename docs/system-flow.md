# Fluxo do sistema — addon, backend, frontend, GitHub, Heroku

Visão de ponta a ponta: como as três aplicações (add-on Anki, backend Django, frontend Next.js) se
comunicam entre si e com a infraestrutura (Supabase, GitHub, Heroku). Detalhes de deploy já ficam em
`docs/deploy.md` e `docs/docker.md` — este doc referencia, não repete.

## Componentes

```mermaid
flowchart LR
    subgraph Local["Máquina do usuário"]
        Anki[Anki Desktop] --> Addon[Add-on ankihub_br]
    end
    subgraph Heroku["Heroku (2 apps, Container Registry)"]
        API[revizza-api<br/>Django + DRF]
        WEB[revizza-web<br/>Next.js]
    end
    subgraph SB["Supabase"]
        PG[(Postgres)]
        Auth[Supabase Auth]
        Storage[Storage / S3]
    end
    Browser[Navegador do usuário] --> WEB
    WEB -- REST API / api/v1 --> API
    WEB -- login/signup direto --> Auth
    Addon -- REST API + Bearer JWT --> API
    API -- ORM / DATABASE_URL pooler --> PG
    API -- valida JWT --> Auth
    API -- signed URL --> Storage
    Addon -- download/upload direto --> Storage
    GH[GitHub main] -- push --> GHA[GitHub Actions]
    GHA -- docker push --> Reg[Heroku Container Registry]
    Reg -- container:release --> API
    Reg -- container:release --> WEB
```

Regra chave: **add-on nunca fala com Supabase Auth diretamente** — ele guarda o JWT que o usuário
obteve (login web ou fluxo próprio do add-on) e manda como `Authorization: Bearer` em toda chamada
ao backend (`addon/ankihub_br/ankihub_br_client/client.py`). O backend é quem valida o token contra
o Supabase Auth (`config/authentication.py`) — nem addon nem frontend confiam em si mesmos, sempre o
backend arbitra.

## Fluxo 1 — Publicar deck (moderador)

```mermaid
sequenceDiagram
    participant Mod as Moderador (Anki + add-on)
    participant API as Backend (revizza-api)
    participant PG as Postgres
    participant ST as Storage

    Mod->>Mod: organiza deck localmente no Anki
    Mod->>API: POST /decks/{id}/publish/ (notes, notetypes, templates, fields, cards)
    API->>PG: persiste em schema 1:1 com SQLite nativo do Anki
    API-->>Mod: URLs assinadas p/ mídia (se houver)
    Mod->>ST: PUT direto na signed URL (upload_signed_media)
```

Import é **create-only**: só funciona em deck inexistente no backend (Constituição, Princípio I).
Depois desse ponto o fluxo vira unidirecional — o add-on nunca republica.

## Fluxo 2 — Assinar e sincronizar (estudante)

```mermaid
sequenceDiagram
    participant U as Usuário (navegador)
    participant WEB as Frontend (revizza-web)
    participant Mod2 as Mesmo usuário no Anki
    participant API as Backend
    participant ST as Storage

    U->>WEB: navega catálogo, clica "assinar"
    WEB->>API: POST /decks/{id}/subscriptions/me/
    Mod2->>API: GET /decks/{id}/sync/delta/?since_mod=...
    API-->>Mod2: notetypes → notes → subdeck reorg (ordem fixa)
    Mod2->>API: GET /decks/{id}/protection/me/ (campos/tags protegidos)
    Mod2->>ST: baixa mídia referenciada (content_hash)
    Note over Mod2,API: se estrutura de notetype mudou de forma não reconciliável,<br/>cai para GET /decks/{id}/sync/full/ (resync completo)
```

Sync é sempre **web → add-on**, nunca o contrário. Campos/tags marcados
`AnkiHubBR_Protect::<Campo>` no lado do usuário não são sobrescritos pelo delta.

## Fluxo 3 — Sugerir → moderar → propagar

```mermaid
sequenceDiagram
    participant U as Usuário
    participant WEB as Frontend
    participant API as Backend
    participant Mod as Moderador (web)
    participant Sync as Outros assinantes (add-on)

    U->>WEB: cria sugestão (mudança/nota nova/exclusão + justificativa)
    WEB->>API: POST .../suggestions/
    Mod->>WEB: revisa em "Community Suggestions" (like/dislike, discussão)
    Mod->>API: aceita/rejeita
    API->>API: se aceita, atualiza nota oficial + entra na fila de sync
    Sync->>API: próximo GET .../sync/delta/ já traz a mudança
```

## Fluxo 4 — GitHub → Heroku (CI/CD)

Resumo (detalhe completo em `docs/deploy.md`):

1. `push`/merge em `main` dispara `.github/workflows/deploy.yml`.
2. Job `test`: pytest (backend) + vitest (frontend) — falha aqui aborta o deploy.
3. Jobs paralelos `build-and-push-backend`/`build-and-push-frontend`: `docker build` +
   `docker push` pro Heroku Container Registry (`backend/Dockerfile` gera `web`+`release`;
   `frontend/Dockerfile` só `web`).
4. Job `release`: `heroku container:release` promove as imagens — backend roda `release`
   (migrations Django) antes de promover `web`.

Sem staging, sem deploy por PR (MVP fechado — Constituição, Princípio V). Add-on **não** entra
nesse pipeline: é `.ankiaddon` empacotado por `addon/build.py` e distribuído fora do CI.

## Papel do Supabase

Externo aos dois apps Heroku, nunca alvo de deploy:

- **Postgres**: única fonte de dados, acessado pelo backend via `DATABASE_URL` (Supavisor
  pooler — conexão direta não funciona no Heroku, ver `docs/deploy.md`).
- **Auth**: emite os JWT que frontend e add-on carregam; backend valida.
- **Storage**: mídia dos decks, sempre via signed URL — add-on e frontend fazem upload/download
  direto no Storage, nunca passam o binário pelo backend.

## Referências

- `docs/deploy.md` — pipeline CI/CD completo, segredos, rollback.
- `docs/docker.md` — build local das imagens.
- `addon/ankihub_br/ankihub_br_client/client.py` — único ponto do add-on que fala HTTP com o backend.
- `backend/config/authentication.py` — validação do JWT do Supabase.
- `.specify/memory/constitution.md` — princípios (import create-only, sync unidirecional, LGPD).
- `PRD-AnkiHub-Brasil.md` §4.1–4.3 — arquitetura e user stories completas.
