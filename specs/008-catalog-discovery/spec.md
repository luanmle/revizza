# Feature Specification: Descoberta avançada do catálogo

**Feature Branch**: `008-catalog-discovery`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "Catálogo: descoberta avançada com abas, informações enriquecidas do card, ordenação escolhível e avatar do criador/moderadores na página do deck."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navegar por abas do catálogo (Priority: P1)

Um usuário que acessa a tela de decks precisa alternar entre todos os decks disponíveis, decks que modera e decks em que está inscrito, sem perder filtros relevantes de descoberta.

**Why this priority**: Segmentação resolve a maior lacuna de descoberta: o usuário não consegue separar catálogo geral, trabalho de moderação e assinaturas atuais.

**Independent Test**: Entrar na tela de decks com usuário autenticado que possui decks moderados e inscritos, alternar entre as três abas e confirmar que cada aba lista apenas o conjunto correto.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado com decks moderados ativos, **When** ele abre a aba "Meus baralhos", **Then** vê exatamente os decks que modera ativamente.
2. **Given** um usuário autenticado com inscrições ativas, **When** ele abre a aba "Inscritos", **Then** vê exatamente os decks em que está inscrito.
3. **Given** qualquer usuário abre a aba "Catálogo", **When** a lista carrega, **Then** vê o catálogo geral sem restrição por moderação ou inscrição.
4. **Given** uma aba sem resultados para o usuário, **When** ela carrega, **Then** um estado vazio claro aparece em vez de erro.

---

### User Story 2 - Avaliar confiança e atividade do deck (Priority: P2)

Um usuário navegando pelo catálogo ou detalhe do deck precisa ver quem criou o deck, quem modera, quando o conteúdo mudou pela última vez, se o deck é oficial e os avatares do criador/moderadores para decidir se confia no material.

**Why this priority**: Sem contexto de autoria, curadoria e atualização, o usuário decide assinatura com pouca confiança.

**Independent Test**: Abrir um deck com criador, moderadores, atualização recente e selo oficial; confirmar que card e detalhe exibem esses sinais de confiança corretamente.

**Acceptance Scenarios**:

1. **Given** um deck com criador identificado, **When** ele aparece no catálogo, **Then** o card exibe nome e avatar do criador quando disponíveis.
2. **Given** um deck com moderadores ativos, **When** o usuário abre a página do deck, **Then** vê avatares dos moderadores ativos junto às informações de moderação.
3. **Given** um deck cujo conteúdo foi alterado recentemente, **When** o card ou detalhe é exibido, **Then** a data relativa de atualização reflete a alteração de conteúdo mais recente, não apenas a data de publicação.
4. **Given** um deck marcado como oficial por equipe autorizada, **When** o card ou detalhe é exibido, **Then** o selo "Oficial" aparece.
5. **Given** um moderador comum acessa seu deck, **When** ele tenta influenciar o selo oficial pelo fluxo normal de moderação, **Then** não consegue se autocertificar como oficial.

---

### User Story 3 - Ordenar resultados de descoberta (Priority: P3)

Um usuário precisa escolher a ordem dos decks conforme objetivo atual: recomendados, populares, atualizados recentemente, com mais notas ou publicados recentemente.

**Why this priority**: Ordenação escolhível melhora descoberta sem criar novas telas.

**Independent Test**: Aplicar cada ordenação disponível e confirmar que a lista muda para o critério escolhido, mantendo aba e filtro por tag quando presentes.

**Acceptance Scenarios**:

1. **Given** o usuário está no catálogo, **When** escolhe "Mais populares", **Then** os decks aparecem em ordem de popularidade.
2. **Given** o usuário escolhe "Atualizados recentemente", **When** a lista carrega, **Then** decks com conteúdo atualizado mais recentemente aparecem antes dos demais.
3. **Given** o usuário troca de aba ou ordenação, **When** a nova lista carrega, **Then** a paginação recomeça do início para evitar resultados pulados ou duplicados.
4. **Given** um filtro por tag já está aplicado, **When** o usuário troca aba ou ordenação, **Then** o filtro por tag continua aplicado.

### Edge Cases

- Usuário não autenticado só vê a aba de catálogo geral; abas pessoais exigem autenticação ou mostram chamada clara para entrar.
- Deck sem criador identificável exibe autoria como indisponível, sem quebrar card ou detalhe.
- Criador original que deixou de moderar continua exibido como fato histórico de autoria.
- Deck sem alterações de conteúdo usa a data de criação como atualização inicial.
- Avatares ausentes usam fallback visual consistente com perfil sem imagem.
- Empates de ordenação preservam ordem estável entre páginas.
- Trocar aba, tag ou ordenação descarta cursor/página anterior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Sistema MUST oferecer três visões de descoberta: "Catálogo", "Meus baralhos" e "Inscritos".
- **FR-002**: "Catálogo" MUST listar decks disponíveis para descoberta geral, sem restringir por inscrição ou moderação do usuário.
- **FR-003**: "Meus baralhos" MUST listar apenas decks em que o usuário é moderador ativo.
- **FR-004**: "Inscritos" MUST listar apenas decks com inscrição ativa do usuário.
- **FR-005**: Sistema MUST preservar combinação de aba, tag e ordenação durante navegação e compartilhamento do estado da lista.
- **FR-006**: Sistema MUST exibir estado vazio claro para abas pessoais sem resultados.
- **FR-007**: Cards de deck MUST exibir nome do criador, avatar do criador quando disponível, última atualização de conteúdo, contagem de notas, contagem de assinantes, tags relevantes e selo oficial quando aplicável.
- **FR-008**: Página de detalhe do deck MUST exibir avatares do criador e dos moderadores ativos quando disponíveis.
- **FR-009**: Última atualização MUST representar a alteração de conteúdo mais recente do deck, com fallback para criação quando não houver alteração posterior.
- **FR-010**: Sistema MUST manter autoria original como fato histórico mesmo se o criador deixar de moderar o deck.
- **FR-011**: Sistema MUST permitir que apenas equipe autorizada marque ou desmarque um deck como oficial.
- **FR-012**: Moderadores comuns MUST NOT conseguir marcar seus próprios decks como oficiais por fluxos de moderação do deck.
- **FR-013**: Sistema MUST oferecer ordenação por recomendados, mais populares, atualizados recentemente, maior quantidade de notas e publicados recentemente.
- **FR-014**: Ordenação padrão MUST continuar sendo recomendados.
- **FR-015**: Cada ordenação MUST ser estável entre páginas, sem pular ou repetir decks quando o usuário avança na lista sem mudar filtros.
- **FR-016**: Alterar aba, tag ou ordenação MUST reiniciar a paginação do início.
- **FR-017**: Tela de decks MUST permanecer usável em viewport de 360px sem rolagem horizontal.
- **FR-018**: Experiência visual da tela de decks MUST passar pelo fluxo de design aprovado para fundação visual e auditoria antes de envio.

### Key Entities

- **Deck**: item de catálogo descoberto pelo usuário; contém identidade, descrição, contadores, tags, selo oficial e sinais de atualização.
- **Creator**: usuário reconhecido como autor original do deck; exibido como contexto histórico de autoria.
- **Moderator**: usuário ativo responsável por moderação do deck; usado para aba pessoal e exibição no detalhe.
- **Subscription**: relação ativa entre usuário e deck; usada para aba de inscritos.
- **Deck Discovery State**: combinação de aba, tag, ordenação e posição de página usada para listar decks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% dos usuários autenticados conseguem alternar entre catálogo geral, decks moderados e decks inscritos em menos de 10 segundos.
- **SC-002**: 100% dos decks oficiais exibem selo oficial em card e detalhe; 0% dos decks não oficiais exibem o selo.
- **SC-003**: 100% dos cards com criador disponível exibem autoria e avatar ou fallback visual.
- **SC-004**: 100% das opções de ordenação retornam resultados na ordem esperada e sem repetição ou salto em navegação paginada contínua.
- **SC-005**: Filtro por tag combinado com aba e ordenação mantém resultados corretos em 100% dos cenários testados.
- **SC-006**: Usuários em viewport de 360px conseguem usar abas, filtro, ordenação e abrir detalhes sem rolagem horizontal.

## Assumptions

- "Meus baralhos" significa decks que o usuário modera ativamente, não apenas decks que criou.
- Selo oficial é controlado por equipe autorizada em área administrativa ou fluxo equivalente fora da moderação comum.
- Não haverá preferência persistida de ordenação no perfil nesta versão; o padrão segue recomendados.
- Página do deck mostra moderadores ativos; moderadores removidos não aparecem como moderadores atuais.
- Avatares usam dados de perfil já existentes; upload/edição de avatar não faz parte desta feature.
