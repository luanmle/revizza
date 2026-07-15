# Phase 0 Research: Sinalização de Sincronização Pendente

## Decision 1 — Fonte de verdade do sinal de pendência

**Decision**: Reaproveitar a `Notification` `sync_pending` já existente (feature 005,
`apps.notifications`) como o único sinal de "há mudança aceita não sincronizada" para (assinante,
deck) — não recalcular a partir de `mod`/`structure_changed_at` numa segunda lógica.

**Rationale**: `apps/sync/views.py::_SubscriberSyncView.get` já cria (via `notify_suggestion_decided`
em accept) e resolve (após sync bem-sucedido, exceto no redirect `full_resync_required`) exatamente
esse par (recipient, deck) com uma constraint parcial garantindo no máximo uma notificação ativa. Isso
já é FR-005/FR-006 da feature 005. Recalcular do zero a partir do delta duplicaria a lógica e arrisca
duas respostas divergentes para "está atualizado?" (Constituição Princípio I).

**Alternatives considered**: Consultar `Note.mod`/`NoteType.structure_changed_at` diretamente contra
um `since_mod` por assinatura — rejeitado porque exigiria uma segunda trilha de "o que mudou" além da
notificação já existente, e o rascunho original já identificou o risco de duas lógicas divergentes.

## Decision 2 — Distinguir "nunca sincronizou" de "sincronizado e atualizado"

**Decision**: Adicionar `Subscription.last_synced_at` (nullable, `DateTimeField`), atualizado para
`timezone.now()` a cada chamada bem-sucedida de `_SubscriberSyncView.get` (delta ou full), independente
de haver ou não uma `Notification` `sync_pending` ativa para resolver.

**Rationale**: Sem esse campo não há como distinguir "usuário nunca sincronizou este deck" (US1,
onboarding) de "usuário sincronizou e está tudo em dia" (nenhuma pendência) — a `Notification`
`sync_pending` só existe quando há mudança aceita depois da assinatura; sua ausência é ambígua entre
os dois estados. Um timestamp simples resolve sem nova tabela.

**Alternatives considered**: Inferir "nunca sincronizou" pela ausência de qualquer registro de sync —
rejeitado porque hoje não existe nenhum registro de sync bem-sucedido persistido (só o rate-limit
efêmero em cache); adicionar o campo é mais simples que reconstruir isso de outra fonte.

## Decision 3 — Superfície do sinal para o add-on

**Decision**: Adicionar um campo `pending_sync: bool` ao serializer já consumido por
`client.get_subscribed_decks()` (`GET /decks/?subscribed=1` → `DeckSubscribedSerializer`), calculado a
partir da mesma `Notification.sync_pending` ativa — sem endpoint novo.

**Rationale**: O add-on já busca essa lista completa toda vez que abre "Decks inscritos" e no próprio
`sync_all`; adicionar um campo é mais barato que outra chamada de rede, e mantém uma única fonte
(Decision 1). O menu "Decks inscritos" (`gui/__init__.py::show_subscribed_decks`) já teria os dados na
resposta que já busca.

**Alternatives considered**: Endpoint dedicado `GET /decks/pending-sync-count/` — rejeitado por YAGNI;
a lista de decks assinados já é buscada nesse fluxo, um campo a mais nela basta.

## Decision 4 — Superfície do sinal na web

**Decision**: Adicionar `sync_status` (`null | "not_synced_yet" | "up_to_date" | "out_of_date"`) ao
`DeckDetailSerializer` já usado por `/decks/[id]/page.tsx`, calculado a partir de `is_subscribed` +
`Subscription.last_synced_at` + `Notification.sync_pending` ativa para o request user.

**Rationale**: A página de detalhe do deck já é o lugar do rascunho original para exibir os dois
estados (onboarding vs. desatualizado); reaproveitar o mesmo campo/endpoint em vez de criar uma rota
nova respeita FR-007 (uma única fonte de "está atualizado?").

**Alternatives considered**: Endpoint separado `/decks/{id}/sync-status/` — rejeitado por YAGNI; o
detalhe do deck já é buscado ao carregar a página, um campo a mais no mesmo payload evita uma segunda
chamada de rede sem necessidade.

## Decision 5 — Onboarding pós-assinatura

**Decision**: Conteúdo estático (instalar/configurar add-on, autenticar, sincronizar) renderizado no
próprio card/estado `sync_status === "not_synced_yet"` do detalhe do deck — não um fluxo/wizard
separado nem estado persistido.

**Rationale**: A spec (Assumptions) já resolveu a questão em aberto do rascunho a favor da opção mais
simples (um sinal, duas mensagens). Nada no onboarding depende de passos sequenciais forçados — é
puramente instrucional.

**Alternatives considered**: Wizard modal multi-etapa com progresso persistido — rejeitado por YAGNI;
nenhum requisito pede acompanhamento de progresso granular, só clareza do próximo passo.
