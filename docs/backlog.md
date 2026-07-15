## 4. Sinalização de sincronização pendente (indicador + onboarding) — *fusão dos rascunhos 4+5*

> **Nota de fusão**: os antigos itens "Indicador de deck desatualizado no add-on" e "Onboarding do
> assinante" descreviam o mesmo sinal subjacente — "o deck tem mudanças que o usuário ainda não trouxe
> para o Anki" — exibido em dois clientes (add-on e web). Combinados numa spec só para construir o
> sinal uma vez e evitar duas lógicas divergentes de "está atualizado?".

### Problema

Sync é unidirecional e manual ("Sincronizar agora"). O usuário não tem sinal de **quando** vale a pena
sincronizar — abre o Anki sem saber se o deck web mudou desde o último sync (o backend já tem o dado,
`mod`/`structure_changed_at` por nota/tipo, usado em `sync/views.py` delta, só não é exposto como "há N
mudanças novas"). O mesmo vazio de sinal aparece na primeira experiência: o caminho catálogo → assinar →
instalar/configurar add-on → primeiro sync tem várias telas (`/decks`, `/decks/[id]`, add-on) sem fio
condutor — SC-006 do MVP mede "cadastro → primeiro login < 2 min", mas não cobre "assinei um deck →
estou estudando no Anki", o momento de maior abandono.

### Escopo (rascunho)

- Endpoint leve (ou campo no detalhe do deck) que responde "há mudanças desde o `mod` local X?" sem
  baixar o delta inteiro — reaproveita a lógica delta que já existe, não reabre o contrato de sync.
- **Add-on**: badge/aviso no menu "Decks inscritos" quando algum deck tem mudanças pendentes.
- **Web**: mesmo sinal usado para o estado "você ainda não sincronizou este deck" no detalhe do deck
  (`/decks/[id]`) — cobre tanto o assinante recém-inscrito (onboarding) quanto o assinante antigo com
  deck desatualizado (uso contínuo).
- Onboarding: após a primeira inscrição na web, guiar o usuário até o add-on (instruções contextuais,
  link de download, "cole este código / faça login").
- Passar pelo pipeline `ui-ux-pro-max` → `impeccable` (Constituição VII) — é superfície de frontend.

### Âncoras

- `backend/apps/sync/views.py` — `DeltaView`, cálculo de `since`/`structure_changed_at`
- `addon/ankihub_br/main/sync.py`, `addon/ankihub_br/gui/__init__.py` — menu "Decks inscritos"
- `frontend/src/app/decks/[id]/page.tsx`, `frontend/src/app/decks/page.tsx`
- `addon/ankihub_br/auth.py` — fluxo de login/conexão do add-on

### Critérios de aceite (rascunho)

- Add-on mostra aviso no menu "Decks inscritos" quando há mudança pendente em algum deck assinado.
- Detalhe do deck na web mostra "não sincronizado ainda" para quem acabou de assinar e "desatualizado"
  para quem já sincronizou mas há mudanças novas — mesmo endpoint, dois textos conforme o estado.
- Assinante recém-cadastrado consegue ir do catálogo até o primeiro sync guiado, sem precisar adivinhar
  o próximo passo.

### Aberto

- [NEEDS CLARIFICATION: o texto/onboarding de primeira vez e o badge de "desatualizado" contínuo
  merecem UX distinta (uma é jornada única, outra é estado recorrente) — decidir se é um único
  componente com dois modos ou dois componentes que consultam o mesmo endpoint.]

## 5. Edição de perfil: foto e demais dados

### Problema

A edição de perfil hoje é parcial. O **nome já é editável** (`MeView.patch` +
`ProfileUpdateSerializer` com `fields = ["name"]` em `backend/apps/accounts/serializers.py:49`; form em
`frontend/src/app/account/page.tsx`), mas:

- **Não existe foto/avatar** — o modelo `User` (`backend/apps/accounts/models.py:6-29`) não tem campo de
  imagem. O perfil é só texto.
- **`target_career`/`target_board` não são editáveis pela tela** — existem no modelo
  (`target_career` com `choices` fiscal/policial/juridica/outra, `target_board` texto livre) mas só são
  gravados no cadastro (`RegisterView`, se aplicável) e nunca mais. Um concurseiro muda de carreira-alvo
  com frequência (trocou de foco de concurso); hoje não há como refletir isso no perfil sem editar direto
  no banco.

Sem avatar, autoria de sugestões, comentários e a lista de moderadores ficam impessoais (só nome/e-mail),
o que reduz confiança e senso de comunidade.

### Escopo (rascunho)

- Adicionar campo de avatar ao `User` (referência à imagem no storage, não o binário no banco).
- **Upload via Supabase Storage** — reaproveitar a infra que já existe para mídia de nota
  (`backend/apps/sync/management/commands/provision_media_bucket.py`, URLs pré-assinadas). Não introduzir
  novo mecanismo de storage (YAGNI / Princípio VI).
- Estender `ProfileUpdateSerializer`/tela `/account` para avatar **e** um seletor de `target_career`
  (dropdown das 4 opções já existentes em `User.TargetCareer`) + campo texto `target_board` — mudar
  carreira-alvo fica tão simples quanto mudar o nome hoje.
- Validar imagem server-side: tipo/tamanho/dimensão máximos; nunca confiar no client.
- Expor o avatar nos lugares que hoje mostram autor: sugestões, comentários (`apps/discussions`),
  lista de moderadores.
- Frontend passa pelo pipeline `ui-ux-pro-max` → `impeccable` (Constituição VII) — é superfície de UI.

### Âncoras

- `backend/apps/accounts/models.py:6-29` — `User`; onde entra o campo de avatar
- `backend/apps/accounts/serializers.py` — `ProfileUpdateSerializer` (`fields = ["name"]` hoje)
- `backend/apps/accounts/views.py:62-75` — `MeView` (`get`/`patch`)
- `backend/apps/sync/` — padrão de upload/URL pré-assinada de mídia a reutilizar
- `frontend/src/app/account/page.tsx` — form de perfil atual (só nome)

### Critérios de aceite (rascunho)

- Usuário faz upload de uma foto, que passa a aparecer no seu perfil e nos pontos de autoria.
- Upload de arquivo inválido (tipo/tamanho fora do limite) é rejeitado com erro claro.
- Usuário troca `target_career` (ex.: de "fiscal" para "policial") e/ou edita `target_board`; a
  mudança é refletida imediatamente no perfil.
- Editar nome continua funcionando exatamente como hoje (sem regressão).

### Aberto

- [NEEDS CLARIFICATION: avatar tem processamento (resize/thumbnail) ou guarda o original? Definir
  limites e se há geração de variações.]
- [NEEDS CLARIFICATION: trocar `target_career` deve afetar recomendações/filtros de catálogo já
  existentes (`subject_tags`) ou é só metadado de perfil, sem efeito colateral no MVP?]

## 6. Catálogo: descoberta avançada (abas, informações do card, ordenação) — *fusão dos rascunhos 7+8+9*

> **Nota de fusão**: os três rascunhos originais ("Categorias no catálogo", "Card do deck: criador/
> última atualização/badge oficial", "Ordenação escolhível") tocam a mesma tela e a mesma view
> (`DeckListView`/`CatalogPagination` em `catalog/views.py`, `DeckSerializer` em `catalog/serializers.py`,
> `frontend/src/app/decks/page.tsx`). O rascunho de ordenação já dependia explicitamente do de
> `last_updated_at` do card. Especificar os três juntos evita reabrir a mesma view três vezes e permite
> decidir de uma vez como abas, ordenação e filtro de tag combinam nos query params.

### Problema

A tela `/decks` só lista o catálogo geral sem segmentação, sem contexto de confiança por deck e com
ordenação fixa — três lacunas independentes na mesma experiência de descoberta:

- **Sem categorias**: o backend **já suporta** filtrar por inscrição — `DeckListView.get_queryset`
  (`backend/apps/catalog/views.py:38-45`) aceita `?subscribed=` e filtra
  `subscriptions__user=request.user` — mas só o add-on consome esse parâmetro
  (`addon/ankihub_br/main/sync.py`), nunca a web. Não existe filtro nenhum para "baralhos que eu
  modero" (`DeckModerator`).
- **Card pobre em contexto**: o card (`decks/page.tsx:128-158`) mostra só nome, contagem de
  notas/assinantes e tags — nada sobre quem criou, quando mudou pela última vez, ou se é curado pela
  equipe ("oficial"). Nenhum desses três dados tem campo pronto:
  - **Criador**: implícito — o `DeckModerator` mais antigo sem `invited_by`, criado no `publish`
    (`sync/views.py:297`). Exige anotação de query, não é campo direto.
  - **Última atualização**: `Deck.updated_at` (`BaseModel`, `base.py:23-26`, `auto_now=True`) **não
    serve sozinho** — só muda no `publish` inicial (`sync/views.py:318`); updates de
    `subscriber_count` usam `.update()` (não dispara `auto_now`); sugestões aceitas alteram `Note`, não
    `Deck`. "Última atualização de conteúdo" precisa ser `max(Note.mod)` das notas do deck.
  - **Badge oficial**: não existe nenhum campo `is_official` no modelo `Deck`. Feature nova.
- **Ordenação fixa**: `CatalogPagination.ordering = ("-recommended", "-subscriber_count",
  "-created_at")` (`views.py:25-27`) — sem parâmetro de escolha (mais popular, mais notas, última
  atualização, etc.).

### Escopo (rascunho)

Três user stories dentro da mesma spec, para caber num único ciclo `/speckit-specify` →
`/speckit-plan` → `/speckit-tasks`:

**US-A — Abas do catálogo**
- Abas na tela `/decks`: **Catálogo** (default), **Meus baralhos** (`DeckModerator` ativo),
  **Inscritos** (reaproveita `?subscribed=` existente).
- Backend: reaproveitar `?subscribed=` como está; novo filtro `?moderated=` em `DeckListView`, mesmo
  padrão do existente, sem endpoint novo.

**US-B — Informações do card**
- `DeckSerializer`/`DeckDetailSerializer`: anotar `creator` (moderador mais antigo sem `invited_by`) e
  `last_updated_at` (`max(notes__mod)`, fallback `created_at`).
- Novo campo `Deck.is_official` (boolean, default `False`). Quem marca **não é o próprio moderador**
  (autocertificação não faz sentido para selo de curadoria) — provavelmente staff/admin Django, fora
  do fluxo normal de moderação.
- Exibir criador + "atualizado há X" + badge "Oficial" no card e no detalhe.

**US-C — Ordenação**
- Parâmetro `?sort=` em `GET /decks/`: `recommended` (default), `popular` (`-subscriber_count`),
  `updated` (usa `last_updated_at` de US-B), `notes` (`-note_count`), `recent` (`-created_at`).
- Cada valor mapeia para uma tupla de `ordering` com desempate fixo no final (`CursorPagination` do DRF
  exige ordenação determinística — sem isso o cursor pula/repete itens entre páginas).
- Seletor simples na tela, combinável com abas (US-A) e filtro de tag existente.

Todas as três passam pelo pipeline `ui-ux-pro-max` → `impeccable` (Constituição VII) — mesma tela.

### Âncoras

- `backend/apps/catalog/views.py:25-67` — `CatalogPagination`, `DeckListView.get_queryset` (abas +
  ordenação)
- `backend/apps/catalog/serializers.py` — `DeckSerializer`, `DeckDetailSerializer` (card)
- `backend/apps/catalog/models.py` — `Deck`, `DeckModerator`, `Subscription`
- `backend/apps/sync/views.py:297,318` — onde criador e `updated_at` são hoje implicitamente
  estabelecidos
- `backend/apps/base.py:23-26` — `BaseModel.updated_at`
- `backend/config/pagination.py:4-7` — `DefaultCursorPagination`
- `frontend/src/app/decks/page.tsx` — tela única, vira container com abas + seletor + card enriquecido

### Critérios de aceite (rascunho)

- Aba "Meus baralhos" lista exatamente os decks moderados ativamente pelo usuário; "Inscritos" o mesmo
  conjunto que o add-on sincroniza via `?subscribed=`.
- Card mostra criador, "atualizado há X" (refletindo a nota mais recente, não só o publish), e badge
  oficial quando aplicável; moderador comum não consegue se autodeclarar oficial.
- Cada opção de `?sort=` retorna a ordem esperada; paginar não pula/repete decks; trocar de aba ou de
  critério reinicia a paginação do zero.
- Filtro por tag continua funcionando combinado com aba e ordenação.
- Usuário sem inscrição/moderação vê estado vazio claro em cada aba (não erro).

### Aberto

- [NEEDS CLARIFICATION: nome exato das abas — "Meus baralhos" pode confundir "criei" vs. "modero" se a
  moderação for transferida.]
- [NEEDS CLARIFICATION: quem tem permissão para marcar `is_official` — admin Django, papel novo,
  endpoint separado?]
- [NEEDS CLARIFICATION: se o criador original deixar de moderar (`DeckModeratorRemoveView`), o card
  mantém o nome dele como fato histórico ou o campo passa a vazio?]
- [NEEDS CLARIFICATION: manter `recommended` como default sempre, ou permitir fixar preferência de
  ordenação no perfil? YAGNI sugere não persistir no MVP desta feature.]

---

### Como usar este arquivo

1. Escolher o próximo item (ordem = prioridade).
2. Rodar `/speckit-specify` colando o bloco do item como descrição da feature.
3. Deixar `/speckit-plan` → `/speckit-tasks` → `/speckit-implement` seguirem o fluxo padrão.
4. Riscar/remover o item daqui quando a feature virar uma pasta em `specs/`.
