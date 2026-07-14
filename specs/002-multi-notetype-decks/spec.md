# Feature Specification: Suporte a Decks com Múltiplos Tipos de Nota

**Feature Branch**: `002-multi-notetype-decks`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Suporte para upload de decks com tipos de modelos de notas diferentes"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publicar deck com tipos de nota mistos (Priority: P1)

Um criador de deck usa o add-on para importar, pela primeira vez, um deck do Anki que contém notas
de mais de um tipo de nota (ex.: "Básico" e "Cloze Jurídico" no mesmo deck). Hoje a importação inicial
é recusada com "A importação inicial aceita um único tipo de nota por deck."; com esta funcionalidade,
a importação é aceita e todas as notas — de qualquer tipo — chegam ao catálogo web associadas ao seu
tipo de nota correto.

**Why this priority**: É o bloqueio relatado (bug `multi-notetype-import-error`, verdict "invalid"
porque a restrição é comportamento MVP documentado, não defeito) — sem isso, decks reais que misturam
tipos de nota (comum em decks de concurso com cartões "Básico" + "Cloze") simplesmente não podem ser
publicados, o que é a dor original do usuário.

**Independent Test**: Publicar, via add-on, um deck local com notas de 2+ tipos de nota distintos e
confirmar que o deck aparece no catálogo web com o número total de notas e todos os tipos de nota
presentes, sem erro.

**Acceptance Scenarios**:

1. **Given** um deck local do Anki com notas dos tipos "Básico" e "Cloze Jurídico", **When** o criador
   publica o deck pela primeira vez via add-on, **Then** a publicação é aceita e o deck passa a existir
   no catálogo com todas as notas, cada uma associada ao seu tipo de nota original.
2. **Given** um deck local do Anki com um único tipo de nota (caso já suportado hoje), **When** o
   criador publica o deck, **Then** o comportamento permanece idêntico ao atual (nenhuma regressão).
3. **Given** um deck já publicado, **When** o add-on tenta republicá-lo (reimportação), **Then** o
   sistema continua recusando com o erro de deck já existente (Princípio II — importação inicial é
   única, isso não muda).

---

### User Story 2 - Assinante sincroniza e revisa notas de tipos diferentes no mesmo deck (Priority: P2)

Um usuário assinante de um deck que contém múltiplos tipos de nota sincroniza o deck para o Anki local
e revisa os cartões. Cada nota deve renderizar com o template/CSS do seu próprio tipo de nota (não o de
outra nota do mesmo deck), tanto na revisão local no Anki quanto no preview da web.

**Why this priority**: Sem isso, a US1 publicaria os dados mas o consumo (sync + preview) poderia
misturar templates entre tipos de nota — a funcionalidade só entrega valor completo se o conteúdo
puder ser efetivamente estudado depois de sincronizado.

**Independent Test**: Sincronizar um deck com 2 tipos de nota para um perfil Anki limpo e confirmar
que os cartões de cada tipo usam o template/CSS correto; abrir o preview de uma nota de cada tipo na
web e confirmar a mesma coisa.

**Acceptance Scenarios**:

1. **Given** um deck publicado com 2 tipos de nota, **When** um assinante sincroniza pela primeira vez,
   **Then** o Anki local reconstrói os dois tipos de nota (campos, templates, CSS) e cada nota é
   importada sob seu tipo correto.
2. **Given** uma nota de um tipo de nota específico dentro de um deck multi-tipo, **When** um usuário
   abre o preview dessa nota na web, **Then** o preview usa exclusivamente o template/CSS do tipo de
   nota daquela nota.

---

### User Story 3 - Moderador visualiza a composição de tipos de nota do deck (Priority: P3)

Ao publicar ou revisar um deck, o moderador vê quantos tipos de nota distintos o deck contém e quantas
notas existem por tipo, para confirmar que a importação capturou a estrutura esperada.

**Why this priority**: É feedback de confirmação — útil para confiança do usuário, mas o deck já
funciona (US1) e sincroniza corretamente (US2) sem essa visão detalhada.

**Independent Test**: Publicar um deck com 3 tipos de nota e confirmar, na tela de detalhe do deck (ou
na confirmação pós-publicação do add-on), uma contagem de notas por tipo de nota que bate com a origem.

**Acceptance Scenarios**:

1. **Given** um deck publicado com N tipos de nota, **When** o moderador abre o detalhe do deck,
   **Then** ele vê a lista de tipos de nota do deck e a contagem de notas de cada um.

---

### Edge Cases

- O que acontece se duas notas do deck usam tipos de nota com o **mesmo nome** mas estrutura (campos)
  diferente (situação possível no Anki, que distingue tipos por ID interno, não só por nome)? O sistema
  deve tratá-los como tipos de nota distintos no backend, preservando ambas as estruturas.
- O que acontece se um dos tipos de nota do deck estiver malformado (sem campos ou sem templates)? A
  importação inteira deve ser recusada (comportamento já existente para o caso de tipo único é mantido:
  atomicidade da transação de publicação — FR-062 do spec MVP).
- Como o sistema se comporta se o deck tiver um número muito grande de tipos de nota distintos (ex.:
  dezenas)? Deve continuar funcionando sem limite artificial — ver Assumptions para o não-limite
  assumido.
- O que acontece com sugestões de mudança (Community Suggestions) feitas em uma nota de um deck
  multi-tipo? A sugestão deve continuar validando os campos propostos contra o tipo de nota **daquela
  nota específica**, não contra um único tipo de nota "do deck".
- O que acontece com a proteção de campos por usuário (`AnkiHubBR_Protect::<Campo>`) em decks com
  múltiplos tipos de nota? A validação de nome de campo protegido deve continuar sendo feita contra o
  tipo de nota da nota específica sendo protegida, não contra um tipo de nota único do deck.
- Ressincronização completa por mudança estrutural (FR-035 do spec MVP) continua se aplicando por tipo
  de nota individual — uma mudança de estrutura em um dos tipos de nota do deck não deve exigir
  ressincronizar tipos de nota que não mudaram.
- O que acontece se um usuário tentar propor uma sugestão de mudança em lote (bulk) selecionando notas
  de **mais de um** tipo de nota do mesmo deck multi-tipo? O sistema deve recusar essa sugestão em
  lote — uma única proposta de campos só faz sentido aplicada a notas estruturalmente iguais; o
  usuário precisa dividir a sugestão por tipo de nota.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST aceitar a importação inicial de um deck cujas notas pertencem a mais de
  um tipo de nota, em vez de recusar com "A importação inicial aceita um único tipo de nota por deck."
- **FR-002**: O sistema MUST persistir, na importação inicial, um tipo de nota distinto para cada
  estrutura de tipo de nota diferente encontrada no deck (campos, templates e CSS preservados por
  tipo).
- **FR-003**: O sistema MUST associar cada nota importada ao seu próprio tipo de nota, não a um tipo de
  nota único atribuído ao deck inteiro.
- **FR-004**: A importação inicial de um deck multi-tipo MUST permanecer atômica — o deck nunca aparece
  parcialmente publicado no catálogo, mesmo com múltiplos tipos de nota envolvidos (mantém a garantia
  já existente para FR-062 do spec MVP).
- **FR-005**: A sincronização (inicial e delta) MUST entregar ao Anki local todos os tipos de nota
  distintos presentes no deck, cada um com seus próprios campos/templates/CSS, e reconstruir cada nota
  sob o tipo de nota correto.
- **FR-006**: A validação de campos propostos em uma sugestão (change/new_note) MUST usar o tipo de
  nota da nota-alvo específica (ou do tipo de nota escolhido para uma nota nova), não um tipo de nota
  único assumido para o deck.
- **FR-007**: A validação de nomes de campo protegidos (`AnkiHubBR_Protect::<Campo>`) MUST usar o tipo
  de nota da nota específica sendo protegida.
- **FR-008**: A ressincronização completa forçada por mudança estrutural (FR-035 do spec MVP) MUST
  continuar avaliando a mudança por tipo de nota individual, não pelo deck como um todo.
- **FR-009**: O sistema MUST expor, para o deck publicado, a lista de tipos de nota distintos que ele
  contém e a contagem de notas por tipo, para consulta pelo moderador/criador.
- **FR-010**: Decks já publicados antes desta funcionalidade (um único tipo de nota) MUST continuar
  funcionando sem nenhuma alteração de comportamento observável (compatibilidade retroativa).

### Key Entities *(include if feature involves data)*

- **Deck**: passa a se relacionar com **um ou mais** tipos de nota (hoje relaciona-se com exatamente
  um). O conjunto de tipos de nota de um deck é derivado dos tipos de nota de suas notas.
- **NoteType**: continua representando um tipo de nota individual (campos, templates, CSS); nenhuma
  mudança na própria entidade — a mudança é em quantos `NoteType`s um `Deck` pode ter associados.
- **Note**: já se relaciona com um `NoteType` próprio (independente do deck); esta funcionalidade torna
  essa relação individual a fonte da verdade para validação e sincronização, em vez de um tipo de nota
  único herdado do deck.
- **Suggestion**: uma sugestão de nota nova (tipo `new_note`) passa a registrar explicitamente qual dos
  tipos de nota existentes do deck a nova nota deve usar — antes implícito (o único tipo do deck),
  agora uma escolha obrigatória do autor da sugestão dentre os tipos de nota já presentes no deck.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um deck real com pelo menos 2 tipos de nota distintos (ex.: "Básico" + "Cloze") é
  publicado com sucesso via add-on em uma única tentativa, sem precisar ser dividido manualmente em
  múltiplos decks.
- **SC-002**: 100% das notas de um deck multi-tipo sincronizado aparecem no Anki local com o template e
  CSS do seu próprio tipo de nota (nenhuma nota herda o template de outro tipo de nota do mesmo deck).
- **SC-003**: Decks publicados antes desta funcionalidade continuam sincronizando e recebendo sugestões
  sem nenhuma regressão observável pelo usuário.
- **SC-004**: O moderador consegue confirmar, em menos de 10 segundos após publicar, quantos tipos de
  nota distintos e quantas notas por tipo o deck publicado contém.

## Assumptions

- Não há limite artificial no número de tipos de nota distintos por deck — o sistema deve suportar
  qualquer quantidade que um deck real do Anki possa ter, sem um teto arbitrário imposto por esta
  funcionalidade.
- Esta funcionalidade é aditiva: nenhuma migração de dados é necessária para decks já publicados com um
  único tipo de nota, pois cada nota já referencia seu próprio tipo de nota independentemente do deck.
- A distinção entre tipos de nota do Anki é feita pela estrutura interna do tipo (ID/campos/templates),
  não pelo nome — dois tipos de nota com o mesmo nome mas campos diferentes são tratados como tipos
  distintos, replicando o comportamento nativo do Anki.
- Republicação de um deck já existente continua proibida (Princípio II — sincronização unidirecional);
  esta funcionalidade não reabre a importação inicial para decks já publicados.
- Suporte a múltiplos tipos de nota por deck é o item explicitamente citado como extensão pós-MVP em
  `specs/001-ankihub-brasil-mvp/data-model.md` ("pode ser estendido a N no pós-MVP"); esta
  funcionalidade é essa extensão, não uma mudança de escopo não planejada.
- A sugestão de nota nova (`new-note`) passa a exigir a escolha de um tipo de nota apenas quando o
  deck tem 2 ou mais tipos; em um deck de tipo único, a escolha é resolvida automaticamente pelo
  backend sem exigir o campo no payload — garante que FR-010/SC-003 (zero mudança de comportamento
  observável para decks já publicados) valham também para este endpoint específico.
