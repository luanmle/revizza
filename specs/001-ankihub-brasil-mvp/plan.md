# Implementation Plan: AnkiHub Brasil — MVP

**Branch**: `001-ankihub-brasil-mvp` | **Date**: 2026-07-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-ankihub-brasil-mvp/spec.md`

## Summary

Construir a plataforma "AnkiHub Brasil": um catálogo web de decks Anki mantidos pela comunidade,
com um ciclo de sugestão → moderação → sincronização que mantém o Anki local de cada assinante
atualizado automaticamente via add-on nativo, sem nunca sobrescrever conteúdo pessoal protegido.
Abordagem técnica: backend Django + DRF expondo uma API REST no estilo AnkiHub original (paginação
por cursor, rotas com barra final, endpoints de sugestão em lote), Postgres via Supabase como fonte
da verdade com schema mapeável 1:1 às tabelas nativas do Anki, frontend Next.js/React mobile-first,
e um add-on Python (`aqt`/`anki`) que mantém um cache local SQLite/peewee do estado de sincronização
por nota e aplica deltas na ordem tipos de nota → notas → subdecks, com fallback para
ressincronização completa e reversão para backup em caso de falha.

## Technical Context

**Language/Version**: Python 3.12 (backend Django + add-on), TypeScript 5.x / Node.js 20 LTS (frontend Next.js)

**Primary Dependencies**:
- Backend: Django 5.x, Django REST Framework, `django-ratelimit` (rate limiting, FR-032/FR-052),
  `nh3` (sanitização de HTML via bindings Rust do `ammonia` — FR-015), `supabase-py` (client para
  Storage/Auth admin), Pillow (validação/normalização de imagem antes do hash de conteúdo).
- Frontend: Next.js 16 (App Router), React 19, Tiptap (editor rich text WYSIWYG sobre ProseMirror
  — FR-014), TanStack Query (cache/estado de chamadas à API), Tailwind CSS 4 + shadcn/ui (preset
  `base-nova`, componentes acessíveis sobre Radix — base de estilo ratificada na Constituição
  v1.1.0, Princípio VII; ver research.md #14).
- Design tooling (dev-only, não runtime): skill `ui-ux-pro-max` gera a fundação visual e o
  `design-system/MASTER.md` persistente; skill `impeccable` audita cada tela (contraste AA,
  hierarquia, FR-055) antes de pronta; componentes shadcn adicionados via MCP.
- Add-on: bibliotecas nativas do Anki (`aqt`, `anki`), `peewee` (cache local SQLite do estado de
  sincronização por nota — citado no PRD §4.1), `requests` (HTTP contra a API), todas vendorizadas
  dentro do pacote `.ankiaddon` no build (sem `pip install` em runtime — PRD §4.6); testes rodam com
  `pytest` puro contra `anki.collection.Collection` headless (pytest-anki 1.0.0b7 é PyQt5-only,
  incompatível com anki>=25/Qt6 — reavaliar se ganhar release Qt6; ver `addon/requirements.txt`).

**Storage**: PostgreSQL via Supabase (fonte da verdade — decks, notas, tipos de nota, sugestões,
comentários, denúncias); Supabase Storage para mídia (imagens); SQLite nativo do Anki + tabela
própria via peewee no cliente (estado de sincronização por nota, não replicado ao servidor).

**Testing**: pytest + pytest-django + `factory_boy` (backend, incluindo testes de contrato da API);
Vitest + React Testing Library (unidade/componentes do frontend) + Playwright (fluxos E2E críticos:
cadastro→assinatura→sugestão→moderação); `pytest` puro contra `anki.collection.Collection` headless
(add-on — pytest-anki é PyQt5-only e incompatível com anki>=25/Qt6, então os testes instanciam a
`Collection` real headless sem plugin nem display gráfico), executado contra a LTS mais recente antes
de cada release; a LTS anterior é exercitada apenas de forma defensiva, sem constituir compromisso de
suporte (FR-038 restringe o suporte do MVP à LTS mais recente — PRD §4.6).

**Target Platform**: Heroku Common Runtime (dyno Linux, região US) para o backend; navegadores
web modernos (mobile-first, 360px+) para o frontend; Windows/macOS/Linux onde roda o Anki Desktop
(apenas a versão LTS mais recente é suportada — FR-038) para o add-on.

**Project Type**: Aplicação web (frontend + backend) mais um add-on desktop nativo — 3 componentes
com ciclos de deploy independentes.

**Performance Goals**: Busca de notas e transições de página em até 500ms para decks de até 10 mil
notas (FR-010, FR-054); sincronização incremental por delta (não repuxa o deck inteiro a cada vez).

**Constraints**: Após a importação inicial única de um deck inexistente pelo criador via add-on,
sincronização sempre unidirecional (web → Anki local, nunca o contrário); republicação ou merge
de edições locais pelo add-on é proibido e a importação responde `409` se o deck já existir;
intervalo mínimo de 10s entre sincronizações do mesmo usuário (FR-032); toda tela funcional em
360px de largura sem rolagem horizontal (FR-053); toda tela atende requisitos básicos de
acessibilidade — labels em formulários, contraste AA, operação via teclado (FR-055); toda a
interface em pt-BR, sem outros idiomas no MVP (FR-056); o preview de
nota é visualmente isolado do design system do frontend, preservando fielmente o template/CSS
original do Anki (FR-011, ver research.md #13); todo HTML de campo rich-text sanitizado antes de
persistir/renderizar (FR-015); nenhuma fila assíncrona (Celery/Redis) no MVP — está no roadmap v1.1
do PRD, fora de escopo aqui (ver Constituição, Princípio V); backend versiona a API via header
`Accept` e mantém compatibilidade com a versão de contrato anterior por um período de transição,
pois o AnkiWeb não força atualização imediata do add-on instalado (PRD §4.6, §5.2); add-on não pode
depender de `pip install` em runtime — toda dependência de terceiro é vendorizada no `.ankiaddon`;
código frontend/backend segue a disciplina ponytail (mínimo necessário, sem abstração especulativa)
e consulta documentação atual via context7 antes de usar API de biblioteca (Constituição v1.1.0,
Princípio VI).

**Scale/Scope**: Baseline de MVP de ~500 usuários e 20 decks nos primeiros 3 meses (SC-001); decks
de até 10 mil notas (RNF-002); 13 user stories / 54 requisitos funcionais do spec.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Como o plano atende |
|---|---|---|
| I. Parity Over Reinvention | PASS | API segue as convenções já observadas do AnkiHub original: DRF `CursorPagination` (campo `next`), rotas com barra final, endpoint de sugestão em lote (`bulk-change-suggestions`), convenção de tag `AnkiHubBR_Protect::<Campo>`. A estrutura interna do add-on (`main/db/*_client/gui`), os hooks usados (`profile_did_open`/`sync_did_finish` + monkey-patch pontual em `AnkiQt._sync_collection_and_media`) e o versionamento de API via header `Accept` também replicam o add-on/backend real (PRD §4.6) em vez de redesenhados do zero. |
| II. Unidirectional Sync — Web Is the Source of Truth | PASS | O add-on permite somente a importação inicial autenticada em um deck inexistente; a rota responde `409` a qualquer republicação. Depois do primeiro snapshot oficial, toda contribuição de conteúdo passa pelo fluxo de sugestão. Backup automático + reversão em falha (FR-039) e fallback para resync completo (FR-035) são parte do design da Fase 1 (ver data-model.md e contracts/sync.md). |
| III. Privacy & LGPD Compliance by Design | PASS | Consentimentos granulares, exclusão com carência de 7 dias e exportação em JSON são campos/endpoints de primeira classe no data model e nos contratos (accounts.md), não uma adição posterior. |
| IV. Secure by Default | PASS | `nh3` sanitiza todo HTML de campo rich-text no backend antes de persistir (FR-015); HTTPS obrigatório via Heroku/Supabase (ambos forçam TLS); `django-ratelimit` nos endpoints de sync e sugestão (FR-052); senha nunca gerenciada por código próprio (Supabase Auth). |
| V. MVP Scope Discipline (YAGNI) | PASS | Sem Celery/Redis, sem notificações assíncronas, sem Optional Tag Groups, sem hierarquia de moderador — todos deferidos ao v1.1/v2.0 conforme PRD §2.3/§5.1. E-mails transacionais (verificação, recuperação de senha) usam o mecanismo nativo do Supabase Auth em vez de infraestrutura própria. |
| VI. Current Docs & Minimal Code (context7 + ponytail) | PASS | Nenhuma API de biblioteca é usada por memória — Tiptap, TanStack Query, shadcn e a doc vendorizada do Next.js 16 (`frontend/node_modules/next/dist/docs/`) são consultadas via context7 antes do uso (regra registrada em `frontend/AGENTS.md`). Código segue ponytail (solução mínima, nativo/stdlib antes de dependência nova); diffs de frontend passam por `/ponytail-review` antes de merge. |
| VII. Design Tooling Pipeline (ui-ux-pro-max + impeccable) | PASS | Tailwind CSS 4 + shadcn/ui instalados e com build verificado (research.md #14); `impeccable` já roda como hook automático em toda edição de frontend. Pendência rastreada (não bloqueia o gate): `design-system/MASTER.md` ainda não gerado — tarefa de setup antes das telas de US4/US5 (ver tasks.md). |

Nenhuma violação identificada — Complexity Tracking permanece vazio.

**Reavaliação pós-Fase 1** (após data-model.md, contracts/ e quickstart.md): nenhuma violação nova
surgiu do design. Pontos que reforçam o PASS original: `Suggestion.status` é modelado como terminal
(sem transição de volta a `pending`), reforçando o Princípio II; `Comment` tem a invariante de FK
exclusiva (nota XOR sugestão), suportando FR-024 sem tabela extra; nenhuma entidade ou contrato
introduziu fila assíncrona, cache distribuído ou serviço adicional além dos já decididos em
Technology Constraints (Princípio V). `NoteType.css`/`templates` (já modelados) são suficientes
para o isolamento do preview de nota exigido por FR-011 (Princípio VII) sem novo campo — o
`GET /api/v1/notes/{id}/` já expõe o necessário para montar o `srcDoc` do iframe isolado
(research.md #13).

## Project Structure

### Documentation (this feature)

```text
specs/001-ankihub-brasil-mvp/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Fase 0 (/speckit-plan)
├── data-model.md         # Fase 1 (/speckit-plan)
├── quickstart.md         # Fase 1 (/speckit-plan)
├── contracts/             # Fase 1 (/speckit-plan)
│   ├── api-conventions.md
│   ├── accounts.md
│   ├── catalog.md
│   ├── notes.md
│   ├── suggestions.md
│   ├── moderators.md
│   ├── protection.md
│   ├── reports.md
│   └── sync.md
└── tasks.md               # Fase 2 (/speckit-tasks — NÃO criado por /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── config/                  # settings Django (base/dev/prod), urls raiz, wsgi/asgi
├── apps/
│   ├── accounts/             # User profile, consentimentos LGPD, exclusão/exportação (US-01, US-13)
│   ├── catalog/               # Deck, DeckModerator, Subscription (US-02, US-08, US-11)
│   ├── notes/                 # NoteType, Note, MediaFile, busca (US-03)
│   ├── discussions/            # Comment, Report (US-04, US-14)
│   ├── suggestions/             # Suggestion, SuggestionVote, moderação (US-05..US-10)
│   ├── protection/               # ProtectedFieldConfig, ProtectedTagConfig (US-12)
│   └── sync/                      # API voltada ao add-on: upload inicial, deltas, mídia (US-08)
└── tests/
    ├── contract/                   # 1 teste por contrato em contracts/*.md
    ├── integration/                  # fluxos ponta-a-ponta por user story
    └── unit/

frontend/
├── design-system/
│   └── MASTER.md               # paleta, tipografia, tokens, componentes-base (ui-ux-pro-max)
├── components.json              # config shadcn/ui (preset base-nova, alias @/components)
├── src/
│   ├── app/                    # rotas Next.js App Router (catálogo, deck, sugestões, conta)
│   │   └── globals.css           # tokens Tailwind/shadcn (oklch, light/dark via classe `.dark`)
│   ├── components/               # editor rich text (Tiptap), diff viewer, listagens
│   │   └── ui/                     # componentes shadcn (tabs, dialog, form, toast, dropdown)
│   └── lib/                        # cliente de API, hooks TanStack Query, `utils.ts` (shadcn `cn`)
└── tests/
    ├── unit/
    └── e2e/                          # Playwright — fluxos P1 do spec, inclui checagem 360px (FR-053)

addon/
├── ankihub_br/
│   ├── manifest.json                # metadados exigidos pelo AnkiWeb (nome, versão, compatibilidade)
│   ├── config.json                    # preferências expostas na tela de config nativa do Anki
│   ├── entry_point.py                  # registra hooks/monkey-patch na inicialização
│   ├── main/                            # lógica de negócio pura: sync, delta, proteção, sugestões, mídia
│   ├── db/                                # cache local peewee/SQLite (estado de sync por nota)
│   ├── ankihub_br_client/                  # única camada que fala HTTP com o backend (auth, retry/backoff)
│   ├── gui/                                  # menu, diálogos de sugestão/config/login (Qt)
│   └── vendor/                                 # dependências de terceiros vendorizadas no build (peewee, requests)
└── tests/
    └── unit/                                    # pytest-anki — simula gui_hooks e Collection real
```

**Structure Decision**: Três projetos independentes (Option 2 estendida) porque o produto exige três
superfícies de deploy genuinamente distintas — API web, SPA/SSR web e um add-on que roda dentro do
processo do Anki Desktop — cada uma com stack, ciclo de release e ambiente de execução próprios.
Backend organizado por app Django por domínio (não por camada técnica), alinhado às entidades do
data-model.md. A estrutura interna do `addon/` (`main/`, `db/`, `ankihub_br_client/`, `gui/`) replica
literalmente a organização do add-on real do AnkiHub (PRD §4.6) em vez de inventar uma nova — cada
módulo isola uma responsabilidade (lógica pura, cache local, HTTP, UI Qt) para permitir testar
`main/`/`db/` via `pytest-anki` sem depender de uma UI real renderizada. O frontend usa
utility-first (Tailwind) + componentes shadcn em vez de uma pasta `styles/` dedicada — o
`design-system/MASTER.md` (Princípio VII) é a única fonte de verdade visual adicional, consultada
antes de qualquer tela nova.

## Complexity Tracking

*Sem violações da Constitution Check — tabela intencionalmente vazia.*
