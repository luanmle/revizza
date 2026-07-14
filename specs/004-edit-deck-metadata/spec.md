# Feature Specification: Edição de título/descrição/tags do deck pelo moderador

**Feature Branch**: `004-edit-deck-metadata`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Edição de título/descrição do deck pelo criador — o criador/moderador não consegue editar as informações do deck depois de publicado (name, description, subject_tags só são gravados uma vez no publish inicial); assinante em potencial vê título/descrição possivelmente desatualizados, o que prejudica a decisão de assinar."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Moderador atualiza metadados do deck (Priority: P1)

Um moderador ativo de um deck já publicado percebe que o título, a descrição ou as tags de assunto estão desatualizados ou incompletos e precisa corrigi-los para que o catálogo reflita informações corretas para potenciais assinantes.

**Why this priority**: É o núcleo do problema relatado — sem isso a informação do catálogo fica congelada desde a publicação inicial, prejudicando a decisão de assinatura de qualquer usuário.

**Independent Test**: Autenticado como moderador ativo de um deck, editar título/descrição/tags a partir da tela de detalhe do deck e confirmar que o catálogo (list + detail) passa a exibir os novos valores imediatamente para qualquer usuário.

**Acceptance Scenarios**:

1. **Given** um usuário é moderador ativo do deck X, **When** ele altera título, descrição e tags de assunto e salva, **Then** o catálogo (tela de listagem e de detalhe) exibe os novos valores para todos os usuários.
2. **Given** um moderador altera apenas a descrição, **When** ele salva, **Then** título e tags permanecem inalterados e a descrição é atualizada.
3. **Given** um moderador submete um título vazio, **When** ele tenta salvar, **Then** o sistema rejeita a alteração com uma mensagem indicando que o título é obrigatório e nenhum dado é gravado.

---

### User Story 2 - Sistema impede edição por quem não é moderador ativo (Priority: P2)

Um usuário autenticado que não é moderador ativo do deck (assinante comum, moderador com convite ainda pendente, ou usuário sem nenhuma relação com o deck) tenta editar os metadados do deck e deve ser bloqueado.

**Why this priority**: Protege a integridade do catálogo — sem essa restrição qualquer usuário autenticado poderia alterar informações de decks que não administra.

**Independent Test**: Autenticado como assinante (não moderador) ou como moderador com status "pending", tentar editar o deck e confirmar que a tentativa é recusada e nenhum dado muda.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado não é moderador do deck X, **When** ele tenta editar título/descrição/tags do deck X, **Then** a tentativa é recusada e os dados do deck permanecem inalterados.
2. **Given** um usuário é moderador do deck X mas seu convite ainda está pendente (não ativo), **When** ele tenta editar o deck, **Then** a tentativa é recusada.
3. **Given** um usuário não autenticado, **When** ele tenta editar o deck, **Then** a tentativa é recusada.

---

### User Story 3 - Potencial assinante vê a descrição atualizada antes de assinar (Priority: P3)

Um usuário navegando pelo catálogo, ainda não assinante do deck, visita a página de detalhe e vê o título/descrição/tags mais recentes para decidir se assina.

**Why this priority**: É a consequência de negócio da US1 (o motivo do pedido), mas depende dela existir — sem edição funcionando não há o que exibir de diferente.

**Independent Test**: Como usuário não assinante, abrir a página de detalhe de um deck cujo moderador acabou de editar a descrição e confirmar que o texto exibido é o mais recente, não o da publicação original.

**Acceptance Scenarios**:

1. **Given** um moderador atualizou a descrição do deck X, **When** um usuário não assinante abre a página de detalhe do deck X, **Then** a descrição exibida é a mais recente.

---

### Edge Cases

- O que acontece se dois moderadores do mesmo deck editarem os metadados quase ao mesmo tempo? (última gravação prevalece — comportamento padrão de "last write wins", sem bloqueio otimista nesta versão).
- O que acontece se o moderador enviar tags de assunto duplicadas ou em formato inesperado? Sistema deve normalizar (remover duplicatas) ou rejeitar tags que não sejam uma lista de textos.
- O que acontece com o deck local já sincronizado no Anki do assinante quando o título é alterado na web? Ver FR-006 (decisão de escopo abaixo).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Sistema MUST permitir que um moderador ativo de um deck edite o título (`name`), a descrição (`description`) e as tags de assunto (`subject_tags`) do deck após a publicação.
- **FR-002**: Sistema MUST rejeitar tentativas de edição de metadados do deck por qualquer usuário que não seja moderador ativo daquele deck específico (incluindo moderadores com convite pendente e usuários não autenticados).
- **FR-003**: Sistema MUST validar que o título não fica vazio após a edição.
- **FR-004**: Sistema MUST refletir a mudança imediatamente na listagem e no detalhe do catálogo, visível a todos os usuários (assinantes ou não).
- **FR-005**: Sistema MUST sanitizar o conteúdo da descrição antes de persistir ou renderizar, removendo tags/atributos não permitidos (mesma política de sanitização aplicada a campos de nota ricos, dado o risco de XSS armazenado já identificado no PRD).
- **FR-006**: Alterar o título (`name`) do deck na web MUST NOT disparar renomeação automática do deck local no Anki do assinante no próximo sync — título/descrição/tags são metadados exibidos apenas no catálogo web; o nome do deck local no Anki do usuário não é alterado por esta funcionalidade.
- **FR-007**: Sistema MUST permitir edição parcial (ex.: apenas descrição, mantendo título e tags como estavam).
- **FR-008**: Sistema MUST normalizar as tags de assunto enviadas (remover duplicatas e valores vazios) ou rejeitar o payload se não for uma lista de textos.

### Key Entities

- **Deck**: entidade já existente no catálogo (título, descrição, tags de assunto, contadores de notas/assinantes). Esta funcionalidade adiciona a capacidade de atualizar título/descrição/tags após a criação inicial.
- **DeckModerator**: relação existente entre usuário e deck com status (pendente/ativo) que determina quem pode editar os metadados do deck.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um moderador ativo consegue atualizar título, descrição e tags de um deck e ver a mudança refletida no catálogo em menos de 5 segundos, sem precisar de suporte técnico.
- **SC-002**: 100% das tentativas de edição por usuários não autorizados (não moderadores ativos) são recusadas.
- **SC-003**: 100% dos potenciais assinantes que visitam a página de detalhe de um deck veem a descrição/título/tags mais recentes, nunca uma versão desatualizada da publicação original.

## Assumptions

- Apenas título, descrição e tags de assunto são editáveis por esta funcionalidade; outros dados do deck (notas, tipos de nota, contadores) continuam fora do escopo de edição direta.
- A descrição aceita rich text (HTML), seguindo a mesma política de sanitização já usada para campos de nota (allowlist de tags/atributos), pois é o "texto de venda" do deck e se beneficia de formatação básica (negrito, listas, links).
- Não há histórico de versões/auditoria de edições de metadados nesta versão (fora de escopo, YAGNI até haver demanda concreta).
- "Last write wins" é aceitável para edições concorrentes — não há necessidade de bloqueio otimista ou lock nesta versão.
- Moderadores com status "pending" (convite não aceito) não têm permissão de edição, apenas moderadores "active".
