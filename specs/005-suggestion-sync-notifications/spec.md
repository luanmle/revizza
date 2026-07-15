# Feature Specification: Notificações de Suggestion/Sync

**Feature Branch**: `005-suggestion-sync-notifications`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Notificações de suggestion/sync — autor avisado quando sugestão é aceita/rejeitada, moderador avisado de sugestão nova, assinante avisado de mudança pendente de sync. Canal in-app antes de e-mail."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Autor sabe o resultado da sua sugestão (Priority: P1)

Um usuário envia uma sugestão de mudança para uma nota de um deck. Um moderador aceita ou rejeita essa sugestão. O autor precisa saber o resultado sem precisar voltar à tela "Community Suggestions" para conferir.

**Why this priority**: É o elo do loop suggest → moderate → propagate que hoje é totalmente mudo — sem isso o autor nunca sabe se contribuiu de fato, o que desmotiva novas sugestões.

**Independent Test**: Pode ser testado criando uma sugestão, decidindo-a (accept ou reject) via `SuggestionAcceptView`/`SuggestionRejectView`, e verificando que o autor recebe uma notificação com o resultado e o motivo (quando rejeitada).

**Acceptance Scenarios**:

1. **Given** um usuário autor de uma sugestão pendente, **When** um moderador aceita a sugestão, **Then** o autor recebe uma notificação in-app informando que a sugestão foi aceita.
2. **Given** um usuário autor de uma sugestão pendente, **When** um moderador rejeita a sugestão com um motivo, **Then** o autor recebe uma notificação in-app com o motivo da rejeição.
3. **Given** uma notificação de decisão já entregue, **When** o autor abre a central de notificações, **Then** a notificação some da contagem de não lidas.

---

### User Story 2 - Moderador sabe que há sugestão nova para revisar (Priority: P2)

Um moderador de deck precisa saber que uma nova sugestão chegou na fila de um deck que ele modera, sem precisar checar a tela manualmente todo dia.

**Why this priority**: Sem isso a fila de moderação cresce sem que ninguém saiba — reduz o segundo elo do loop, mas depende do primeiro (autor) estar resolvido para o ciclo completo fazer sentido.

**Independent Test**: Pode ser testado criando uma sugestão nova em um deck com moderadores ativos e verificando que cada moderador ativo do deck recebe uma notificação in-app.

**Acceptance Scenarios**:

1. **Given** um deck com um ou mais moderadores ativos, **When** um usuário cria uma sugestão nesse deck, **Then** todos os moderadores ativos do deck recebem uma notificação in-app sobre a nova sugestão pendente.
2. **Given** um deck sem moderadores ativos, **When** uma sugestão é criada, **Then** nenhuma notificação de moderação é gerada (não há para quem notificar).

---

### User Story 3 - Assinante sabe que há mudanças aguardando sincronização (Priority: P3)

Um assinante de um deck precisa saber que existem mudanças aceitas ainda não puxadas pelo seu add-on local, para decidir quando rodar "Sincronizar agora".

**Why this priority**: Valor de engajamento incremental — o add-on já resolve a sincronização em si; isso só melhora a descoberta de que há algo novo. Menor prioridade porque o loop de moderação (US1/US2) é o gargalo mais urgente hoje.

**Independent Test**: Pode ser testado aceitando uma sugestão em um deck com assinantes e verificando que cada assinante recebe uma indicação (notificação in-app) de que há mudanças pendentes de sync, sem duplicar a cada nova aceitação antes do próximo sync.

**Acceptance Scenarios**:

1. **Given** um assinante de um deck cujo `mod` mais recente é anterior à última sugestão aceita, **When** uma sugestão é aceita nesse deck, **Then** o assinante recebe (ou mantém) uma notificação in-app indicando que há mudanças aguardando sync.
2. **Given** um assinante que acabou de sincronizar via add-on, **When** o sync é concluído, **Then** a notificação de "mudanças pendentes" para aquele assinante é encerrada/marcada como resolvida.

---

### Edge Cases

- O que acontece quando o autor de uma sugestão também é moderador do próprio deck (moderador decide a própria sugestão de outro usuário, ou modera-se a si mesmo)? A notificação de "nova sugestão" não deve ser enviada ao moderador que é o próprio autor da sugestão.
- O que acontece quando um moderador é removido/desativado antes de ver a notificação? Notificações pendentes desse moderador ficam órfãs mas não visíveis (moderador desativado não deve mais ver a central de notificações de moderação do deck).
- O que acontece com uma sugestão decidida em massa (ex.: múltiplas sugestões aceitas na mesma operação)? Cada decisão gera sua própria notificação ao respectivo autor — sem agrupamento no MVP.
- Como o sistema evita notificar o assinante repetidamente a cada nova sugestão aceita antes de ele sincronizar? Deve haver no máximo uma notificação "ativa" de sync pendente por assinante por deck; novas aceitações antes do sync não geram novas notificações, apenas mantêm a existente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE notificar o autor de uma sugestão quando ela for aceita, incluindo referência ao deck e, quando a sugestão afeta uma única nota, à nota afetada (sugestões em lote referenciam apenas deck+sugestão, não uma nota individual).
- **FR-002**: O sistema DEVE notificar o autor de uma sugestão quando ela for rejeitada, incluindo o motivo de rejeição já capturado na decisão.
- **FR-003**: O sistema DEVE notificar todos os moderadores ativos de um deck quando uma nova sugestão for criada nesse deck, exceto quando o próprio moderador for o autor da sugestão.
- **FR-004**: O sistema DEVE indicar a um assinante de um deck que existem mudanças aceitas ainda não sincronizadas em seu add-on local.
- **FR-005**: O sistema DEVE evitar duplicar a notificação de "mudanças pendentes de sync" para o mesmo assinante/deck enquanto ele não sincronizar (no máximo uma notificação ativa por par assinante/deck).
- **FR-006**: O sistema DEVE encerrar/marcar como resolvida a notificação de "mudanças pendentes de sync" de um assinante quando o sync desse assinante for concluído.
- **FR-007**: Usuários DEVEM conseguir visualizar suas notificações em uma central in-app, com indicação de quantas estão não lidas.
- **FR-008**: Usuários DEVEM conseguir marcar notificações como lidas (individualmente ou todas de uma vez).
- **FR-009**: O sistema NÃO DEVE enviar notificações por e-mail neste MVP — apenas in-app (dependência de consentimento LGPD separado fica fora de escopo aqui).
- **FR-010**: O sistema DEVE reter notificações lidas por até 90 dias antes de poderem ser descartadas (job de limpeza periódico, não bloqueante para o MVP).

### Key Entities *(include if feature involves data)*

- **Notification**: representa um evento a comunicar a um usuário específico. Atributos: destinatário, tipo (sugestão aceita, sugestão rejeitada, nova sugestão para moderar, sync pendente), referência ao deck/sugestão/nota relacionados, estado (não lida/lida/resolvida), timestamp de criação.
- **Suggestion** (existente, `apps/suggestions`): fonte de eventos para as notificações de decisão e de nova sugestão.
- **Deck subscription** / **moderator** (existente): define os destinatários das notificações de moderação e de sync pendente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Autores conseguem saber o resultado de uma sugestão decidida sem navegar manualmente até a tela de sugestões — visível na central de notificações em até alguns segundos após a decisão do moderador.
- **SC-002**: Moderadores conseguem identificar sugestões pendentes novas pela central de notificações, sem precisar checar a tela do deck proativamente todo dia.
- **SC-003**: 100% das decisões de sugestão (accept/reject) geram exatamente uma notificação para o autor correspondente.
- **SC-004**: Nenhum assinante recebe mais de uma notificação ativa de "sync pendente" simultânea para o mesmo deck.

## Assumptions

- **Desvio de escopo explícito (Princípio V)**: PRD §2.3 lista "notificações" entre itens adiados
  para v1.1, empacotados junto com fila assíncrona (Celery+Redis). Esta spec puxa notificações para
  o MVP deliberadamente — o loop suggest→moderate→propagate hoje é mudo, o que é pior para
  engajamento do que o custo de construir a central agora. Fila assíncrona NÃO é puxada junto:
  volume esperado (uma sugestão decidida por vez) não justifica infra de fila — escrita síncrona
  dentro da própria view basta. Revisitar fila se volume por deck crescer a ponto de decisões em
  massa (accept bulk) tornarem a criação de notificação um gargalo perceptível na resposta.
- Notificações são por usuário (não por e-mail/lista) e in-app apenas — canal e-mail fica para uma fase futura, condicionado ao consentimento LGPD já existente em `accounts`.
- "Moderador ativo" segue a mesma definição já usada por `is_active_deck_moderator` em `apps/suggestions/permissions.py`.
- A notificação de "sync pendente" é por par (assinante, deck), não por sugestão individual — evita ruído quando várias sugestões são aceitas em sequência.
- O modelo de dados de notificação é uma tabela nova (`Notification`), não derivado de estados existentes — porque os eventos (decisão, nova sugestão, sync pendente) têm timing e destinatários distintos que não mapeiam 1:1 para um único campo de status já existente.
- A UI da central de notificações (badge, lista, marcar como lida) é in-app na aplicação web existente, sem push nativo.
