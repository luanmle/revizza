# Feature Specification: Sinalização de Sincronização Pendente (indicador + onboarding)

**Feature Branch**: `006-pending-sync-signal`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Sinalização de sincronização pendente (indicador + onboarding) — fusão dos rascunhos 4+5: indicador de deck desatualizado no add-on + onboarding do assinante, unificados porque descrevem o mesmo sinal subjacente ('o deck tem mudanças que o usuário ainda não trouxe para o Anki') exibido em dois clientes (add-on e web)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assinante recém-inscrito é guiado até o primeiro sync (Priority: P1)

Um usuário acabou de assinar um deck no catálogo web. Ele precisa saber, sem adivinhar, que o próximo
passo é instalar/configurar o add-on e rodar o primeiro sync — hoje esse caminho (catálogo → assinar →
add-on → primeiro sync) não tem fio condutor nenhum.

**Why this priority**: É o momento de maior abandono do funil (assinei mas nunca cheguei a estudar no
Anki). Sem isso, tudo que o produto construiu até aqui — catálogo, assinatura, deck moderado — nunca
chega a virar valor real pro usuário.

**Independent Test**: Assinar um deck com um usuário que nunca sincronizou nada, abrir o detalhe do
deck na web, e verificar que aparece uma indicação clara de "ainda não sincronizado" com o próximo
passo (instalar/configurar add-on, rodar sync).

**Acceptance Scenarios**:

1. **Given** um usuário que acabou de assinar um deck e nunca completou um sync desse deck, **When**
   ele abre o detalhe do deck na web, **Then** vê uma indicação de "ainda não sincronizado" com o
   próximo passo a seguir (instalar/configurar o add-on).
2. **Given** um usuário nessa mesma situação, **When** ele completa o primeiro sync via add-on,
   **Then** a indicação de "ainda não sincronizado" desaparece do detalhe do deck.

---

### User Story 2 - Assinante antigo sabe que o deck tem mudanças novas (Priority: P2)

Um assinante que já sincronizou um deck antes precisa saber, ao visitar o site, que existem mudanças
aceitas desde o último sync dele, para decidir se vale abrir o Anki agora.

**Why this priority**: Cobre o uso contínuo (não só a primeira vez) — sem isso o assinante segue sem
sinal de "vale a pena sincronizar agora?" no dia a dia, mesmo depois de já ter passado pelo onboarding.
Depende do sinal básico da US1 já existir, por isso vem em seguida.

**Independent Test**: Com um assinante que já sincronizou um deck, aceitar uma nova sugestão nesse
deck, abrir o detalhe do deck na web, e verificar que aparece "desatualizado" (não "ainda não
sincronizado").

**Acceptance Scenarios**:

1. **Given** um assinante que já sincronizou um deck e uma sugestão foi aceita depois disso, **When**
   ele abre o detalhe do deck na web, **Then** vê uma indicação de "desatualizado" distinta da
   indicação de primeira vez.
2. **Given** um assinante cujo deck está com tudo sincronizado (nenhuma mudança aceita desde o último
   sync dele), **When** ele abre o detalhe do deck, **Then** não vê nenhuma indicação de pendência.

---

### User Story 3 - Usuário do add-on vê de relance quais decks têm pendência (Priority: P3)

Um usuário do add-on quer saber, olhando o menu "Decks inscritos", quais dos seus decks assinados têm
mudanças pendentes, sem precisar abrir cada um para checar.

**Why this priority**: Valor incremental de conveniência dentro do próprio Anki — a web (US1/US2) já
cobre a descoberta do sinal; isso só evita que o usuário precise abrir cada deck manualmente dentro do
add-on. Menor prioridade porque o add-on já executa o sync sob demanda mesmo sem esse indicador.

**Independent Test**: Com um usuário que tem 2+ decks inscritos, uma sugestão aceita em apenas um
deles, abrir o menu "Decks inscritos" no add-on e verificar que só o deck com pendência aparece
marcado.

**Acceptance Scenarios**:

1. **Given** um usuário com um ou mais decks inscritos, **When** algum desses decks tem mudanças
   pendentes, **Then** o menu "Decks inscritos" do add-on mostra um indicador nesse(s) deck(s).
2. **Given** um usuário cujos decks inscritos estão todos sincronizados, **When** ele abre o menu
   "Decks inscritos", **Then** nenhum indicador de pendência aparece.

---

### Edge Cases

- Deck recém-assinado sem nenhuma mudança aceita ainda desde a assinatura: mostra o passo de
  onboarding (US1), não a indicação de "desatualizado" (US2) — são estados mutuamente exclusivos por
  deck/assinante.
- Assinatura cancelada: o indicador (web ou add-on) para esse par assinante/deck deixa de ser exibido.
- Deck excluído enquanto havia pendência ativa: o indicador correspondente some sem erro visível ao
  usuário.
- Usuário do add-on sem nenhum deck inscrito: menu "Decks inscritos" não mostra nenhum indicador.
- Sync completado pelo add-on enquanto o usuário está com o detalhe do deck aberto na aba web: a
  indicação web deve refletir "sincronizado" na próxima vez que a página for carregada ou consultada
  (não é exigido tempo real/push).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE indicar, por par assinante/deck, se existem mudanças aceitas ainda não
  trazidas para a coleção local desse assinante.
- **FR-002**: A web DEVE mostrar, no detalhe de um deck assinado, um estado "ainda não sincronizado"
  quando o assinante nunca completou um sync desse deck.
- **FR-003**: A web DEVE mostrar, no detalhe de um deck assinado, um estado "desatualizado" quando o
  assinante já sincronizou ao menos uma vez mas há mudanças aceitas depois do último sync dele —
  distinto textualmente do estado "ainda não sincronizado".
- **FR-004**: A web NÃO DEVE mostrar nenhuma indicação de pendência quando o assinante está com o deck
  totalmente sincronizado.
- **FR-005**: O add-on DEVE mostrar, no menu "Decks inscritos", um indicador nos decks que têm mudanças
  pendentes para aquele usuário.
- **FR-006**: Após a primeira assinatura de um deck pelo usuário na web, o sistema DEVE apresentar os
  próximos passos guiados até o primeiro sync (instalar/configurar o add-on, autenticar, sincronizar).
- **FR-007**: O indicador de pendência (web e add-on) DEVE se basear na mesma fonte de verdade de
  "há mudança aceita não sincronizada" — não pode haver duas lógicas divergentes de "está atualizado?"
  entre os dois clientes.
- **FR-008**: O indicador DEVE deixar de mostrar pendência para um par assinante/deck imediatamente
  após esse assinante completar um sync bem-sucedido desse deck.

### Key Entities *(include if feature involves data)*

- **Pending sync signal**: estado por (assinante, deck) indicando se há mudança aceita não trazida
  para a coleção local — já existe como o sinal por trás da notificação `sync_pending` da feature 005
  (`apps.notifications`); esta feature expõe esse mesmo sinal para o detalhe do deck na web e para o
  menu do add-on, em vez de recalculá-lo de outra forma.
- **Deck** (existente): dono do estado de pendência exibido.
- **Subscription** (existente): define quem enxerga o indicador de um deck.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um assinante consegue saber se um deck assinado tem mudanças novas olhando o detalhe do
  deck na web, sem precisar abrir o Anki para descobrir.
- **SC-002**: Um usuário do add-on identifica quais dos seus decks inscritos têm pendência olhando o
  menu "Decks inscritos", sem abrir cada deck individualmente.
- **SC-003**: Ao menos 70% dos novos assinantes completam o primeiro sync do deck assinado dentro de
  24 horas da assinatura.
- **SC-004**: Nenhum assinante com deck totalmente sincronizado vê uma indicação falsa de pendência.

## Assumptions

- **Reaproveitamento do sinal existente**: a feature 005 já mantém, por (assinante, deck), uma
  notificação `sync_pending` ativa exatamente quando há mudança aceita não sincronizada, resolvida no
  sync bem-sucedido. Esta feature reaproveita esse mesmo sinal como fonte de verdade (FR-007) em vez de
  recalcular a partir do delta diretamente — evita duas lógicas divergentes de "está atualizado?"
  (Princípio I).
- **Um sinal, duas mensagens, não dois componentes**: "ainda não sincronizado" (primeira vez) e
  "desatualizado" (uso contínuo) são o mesmo sinal de pendência com dois textos diferentes conforme o
  assinante já tenha ou não um sync anterior completo desse deck — não duas funcionalidades separadas
  (resolve a clarificação em aberto do rascunho original a favor da opção mais simples, YAGNI).
- Onboarding pós-assinatura (FR-006) é conteúdo instrucional estático (instalar add-on, autenticar,
  sincronizar) — não é um fluxo com estado próprio persistido, é orientação de próximo passo derivada
  do próprio estado "ainda não sincronizado".
- Sem tempo real/push: o indicador web reflete o estado na carga da página (ou próxima consulta), não
  precisa atualizar instantaneamente se o sync acontecer em outra aba/dispositivo enquanto a página
  está aberta.
- Superfícies de frontend (detalhe do deck, onboarding) passam pelo pipeline `ui-ux-pro-max` →
  `impeccable` (Constituição VII) antes de considerar a UI pronta.
