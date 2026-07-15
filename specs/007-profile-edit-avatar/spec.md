# Feature Specification: Edição de Perfil (Foto e Dados Adicionais)

**Feature Branch**: `007-profile-edit-avatar`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Edição de perfil: foto e demais dados — adicionar avatar (upload via Supabase Storage) e tornar target_career/target_board editáveis na tela /account, mantendo edição de nome sem regressão."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload de foto de perfil (Priority: P1)

Usuário concurseiro quer subir uma foto para seu perfil, para que sugestões, comentários e a lista de moderadores deixem de mostrar só nome/e-mail.

**Why this priority**: É a lacuna mais visível (perfil hoje é só texto) e afeta confiança/senso de comunidade em toda a plataforma, não só na tela de conta.

**Independent Test**: Usuário autenticado abre `/account`, envia um arquivo de imagem válido, e a foto passa a aparecer no seu próprio perfil imediatamente — testável isoladamente do restante do escopo.

**Acceptance Scenarios**:

1. **Given** usuário autenticado sem avatar definido, **When** ele envia uma imagem válida (tipo e tamanho dentro do limite), **Then** o avatar é salvo e exibido na tela de conta.
2. **Given** usuário já tem avatar, **When** ele envia uma nova imagem, **Then** a imagem antiga é substituída pela nova.
3. **Given** usuário tenta enviar arquivo de tipo não permitido (ex.: `.exe`, `.pdf`) ou maior que o limite de tamanho, **When** o upload é submetido, **Then** o sistema rejeita com mensagem de erro clara e o avatar anterior (se houver) permanece inalterado.

---

### User Story 2 - Avatar visível nos pontos de autoria (Priority: P2)

Outros usuários da plataforma querem ver o avatar de quem sugeriu uma mudança, comentou, ou modera um deck, para dar rosto à autoria do conteúdo.

**Why this priority**: Depende do avatar existir (US1), mas é o que de fato entrega o valor de "reduzir impessoalidade" descrito no problema — sem isso, o avatar fica preso só na própria tela de conta.

**Independent Test**: Com um usuário que já tem avatar (US1), abrir a lista de sugestões, uma thread de comentário, e a lista de moderadores de um deck, e confirmar que o avatar aparece ao lado do nome em cada um.

**Acceptance Scenarios**:

1. **Given** um usuário com avatar enviou uma sugestão, **When** outro usuário visualiza a tela de sugestões da comunidade, **Then** o avatar do autor aparece junto ao nome.
2. **Given** um usuário com avatar comentou em uma discussão, **When** a thread é exibida, **Then** o avatar aparece junto ao comentário.
3. **Given** um usuário com avatar modera um deck, **When** a lista de moderadores do deck é exibida, **Then** o avatar aparece junto ao nome do moderador.
4. **Given** um usuário sem avatar (nunca fez upload), **When** ele aparece em qualquer um dos pontos de autoria acima, **Then** um avatar padrão (placeholder) é exibido no lugar, sem erro.

---

### User Story 3 - Editar carreira-alvo e banca (Priority: P3)

Usuário concurseiro que mudou de foco de concurso quer atualizar `target_career` e `target_board` no próprio perfil, sem precisar de suporte ou edição direta no banco.

**Why this priority**: Resolve uma lacuna funcional real (dado hoje só gravável no cadastro), mas é independente do avatar e tem menor impacto de confiança imediata que US1/US2.

**Independent Test**: Usuário autenticado abre `/account`, seleciona uma nova carreira-alvo em um dropdown e edita o texto da banca, salva, e vê os novos valores refletidos na tela.

**Acceptance Scenarios**:

1. **Given** usuário com `target_career` = "fiscal", **When** ele seleciona "policial" no seletor de carreira-alvo e salva, **Then** o perfil passa a exibir "policial" imediatamente.
2. **Given** usuário edita o campo de texto de `target_board`, **When** ele salva, **Then** o novo valor é persistido e exibido no perfil.
3. **Given** usuário só quer editar o nome (fluxo já existente), **When** ele salva sem tocar em avatar/carreira/banca, **Then** o nome é atualizado exatamente como hoje, sem regressão nos demais campos.

---

### Edge Cases

- Upload de imagem corrompida ou com metadados maliciosos: sistema deve rejeitar ou sanitizar antes de exibir, nunca servir o arquivo bruto sem validação de tipo real (não apenas extensão/nome).
- Usuário remove o avatar (sem enviar um novo): sistema deve permitir voltar ao placeholder padrão.
- Falha de rede/serviço de storage durante o upload: usuário recebe mensagem de erro clara e o restante do formulário (nome, carreira, banca) continua editável e salvável independentemente do avatar.
- Usuário deixa `target_board` em branco: campo é opcional, perfil continua válido sem banca definida.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Sistema MUST permitir que um usuário autenticado envie uma imagem para ser seu avatar de perfil.
- **FR-002**: Sistema MUST validar, no servidor, tipo de arquivo, tamanho e dimensão máxima da imagem antes de aceitar o upload — nunca confiar apenas em validação do cliente.
- **FR-003**: Sistema MUST rejeitar upload inválido com mensagem de erro clara, mantendo o avatar anterior (se houver) inalterado.
- **FR-004**: Sistema MUST substituir o avatar anterior quando um novo upload válido é feito.
- **FR-005**: Sistema MUST exibir o avatar do usuário na própria tela de perfil (`/account`).
- **FR-006**: Sistema MUST exibir o avatar do autor (ou um placeholder padrão, se não houver avatar) em: lista de sugestões da comunidade, threads de discussão/comentários, e lista de moderadores de deck.
- **FR-007**: Sistema MUST permitir que o usuário edite `target_career` através de um seletor com as opções já existentes no modelo (fiscal/policial/jurídica/outra).
- **FR-008**: Sistema MUST permitir que o usuário edite `target_board` como campo de texto livre opcional.
- **FR-009**: Sistema MUST persistir e refletir imediatamente na tela as mudanças de avatar, `target_career` e `target_board` após salvar.
- **FR-010**: Sistema MUST continuar permitindo a edição do nome exatamente como hoje, sem regressão, independentemente de os demais campos serem alterados ou não.
- **FR-011**: Sistema MUST permitir que o usuário remova seu avatar, retornando ao placeholder padrão.

### Key Entities

- **Perfil de usuário**: entidade existente estendida com uma referência a imagem de avatar (armazenada em storage externo, não como binário no banco), além dos campos já existentes `target_career` e `target_board`, agora editáveis.
- **Avatar**: arquivo de imagem associado a um usuário, com metadados de validação (tipo, tamanho); referenciado por URL/caminho a partir do perfil.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuário consegue enviar um avatar e vê-lo refletido no próprio perfil em menos de 10 segundos após o upload.
- **SC-002**: 100% dos uploads com tipo/tamanho fora do limite são rejeitados com mensagem de erro compreensível, sem corromper o avatar existente.
- **SC-003**: Avatar (ou placeholder) aparece corretamente em 100% dos pontos de autoria (sugestões, comentários, lista de moderadores) após o upload.
- **SC-004**: Usuário consegue trocar `target_career`/`target_board` e ver a mudança refletida no perfil sem recarregar a página manualmente.
- **SC-005**: Edição de nome mantém 100% de paridade funcional com o comportamento atual (nenhuma regressão relatada).

## Assumptions

- Avatar armazena a imagem enviada após validação de tipo/tamanho/dimensão, sem pipeline de geração de variações/thumbnails nesta versão — a mesma URL é usada em todos os pontos de exibição, redimensionada apenas via CSS/atributos de exibição no frontend. Gerar thumbnails no servidor fica para uma iteração futura caso o tamanho de arquivo original se mostre um problema de performance real.
- Trocar `target_career`/`target_board` é apenas metadado de perfil nesta versão — não dispara nenhum efeito colateral em filtros, recomendações ou `subject_tags` de catálogo já existentes. Vincular carreira-alvo a filtros de descoberta de decks fica fora de escopo até haver uma necessidade concreta.
- Upload reutiliza a infraestrutura de storage e URLs pré-assinadas já existente para mídia de nota (Supabase Storage), sem novo mecanismo de armazenamento.
- Existe um avatar placeholder padrão para usuários que nunca fizeram upload.
- Usuários têm conectividade estável o suficiente para completar um upload de imagem de perfil padrão (poucos MB).
