# Feature Specification: AnkiHub Brasil — MVP

**Feature Branch**: `001-ankihub-brasil-mvp`

**Created**: 2026-07-12

**Status**: Draft

**Input**: User description: "crie o specify de acordo com o que esta documentado no PRD presente nesse diretorio" (gerar a especificação a partir de `PRD-AnkiHub-Brasil.md`)

## Clarifications

### Session 2026-07-12

- Q: Qual deve ser o intervalo mínimo entre sincronizações consecutivas do mesmo usuário (FR-032, hoje descrito vagamente como "poucos segundos")? → A: 10 segundos.
- Q: Qual meta de tempo para concluir cadastro + primeiro login (SC-006, hoje "poucos minutos")? → A: Menos de 2 minutos.
- Q: Qual a política de compatibilidade de versão do Anki Desktop suportada pelo add-on no MVP? → A: Apenas a versão LTS mais recente.
- Q: Se uma sincronização for interrompida no meio (queda de rede, Anki fechado), qual deve ser o comportamento esperado? → A: Reverter para o backup pré-sync e exigir uma nova tentativa completa (sem retomada parcial).

### Session 2026-07-13

- Q: Que requisitos de acessibilidade se aplicam às telas do frontend, hoje ausentes do spec (fonte: `rascunho-frontend.md`)? → A: Todo formulário tem labels associados aos campos, contraste de texto/fundo em nível AA (WCAG), e todo componente interativo (editor rich text, abas de Community Suggestions, botões de curtir/aceitar/rejeitar) é operável via teclado.
- Q: A renderização fiel de nota (FR-011) pode ser afetada pelo estilo visual do resto da aplicação (design system do frontend)? → A: Não — o preview de nota MUST permanecer visualmente isolado do CSS/tema do restante da aplicação, para que apenas o template/CSS original do Anki determine sua aparência.

### Session 2026-07-14

- Q: Qual nome aparece como menu top-level do add-on no menubar do Anki (e como marca visível do add-on)? → A: "Revizza" — todo o copy pt-BR do add-on usa essa marca; a convenção de tag `AnkiHubBR_Protect::` já implementada permanece inalterada.
- Q: Quais itens compõem o menu Revizza no menubar? → A: Núcleo apenas: Entrar/Sair, Sincronizar agora, Decks inscritos, Criar deck Revizza (upload inicial), Testar conexão — só o que a plataforma atual já suporta.
- Q: O diálogo "Decks inscritos" do add-on permite gerenciar ou só visualizar? → A: Gerenciar básico — listar decks, cancelar inscrição e alterar preferências de sync (gatilhos automático/encadeado e apagar vs marcar nota removida) direto no add-on, absorvendo o antigo item "Preferências" (mesmo domínio por-deck, sem conceito de preferência global no produto); inscrever-se em deck novo continua exclusivo da web.
- Q: Como fica a configuração de URL da API depois de pré-configurada? → A: Escondida — URL de produção embutida como constante única no pacote, ausente da UI; override apenas pelo config.json avançado do Anki (dev/teste); o usuário só precisa logar.
- Q: O que o botão "Testar conexão" verifica? → A: API + sessão — sempre testa o alcance da API por endpoint público leve (sem auth) e, se houver sessão, valida também o token; reporta dois sinais distintos ("API ok" e "Sessão ok/expirada").
- Q: FR-052 não quantifica a taxa de submissão de sugestões (distinta dos 10s de FR-032 para sync). Qual limite? → A: 20 submissões por minuto por usuário — valor já implementado em produção; o spec apenas formaliza.
- Q: Comportamento esperado quando uma dependência externa crítica (Supabase Auth/DB, e-mail, Storage) fica indisponível? → A: Erro genérico e legível em pt-BR reportado ao Sentry, sem retry automático nem modo degradado dedicado — escopo mínimo suficiente para o MVP/teste fechado.
- Q: Se o job de exclusão de conta (FR-046) ou o e-mail de notificação de remoção (FR-050) falhar, o que acontece? → A: O job de exclusão é idempotente e reexecuta na próxima janela agendada até concluir; falha de e-mail nunca bloqueia a ação principal (dado deletado ou conteúdo removido não espera confirmação de envio); erros vão ao Sentry, sem retry imediato nem alerta ativo.
- Q: A importação inicial de deck precisa ser transação única incluindo mídia, ou tolera mídia em melhor-esforço? → A: Deck/tipo de nota/notas committam em uma única transação atômica (nunca existe deck "meio publicado" no catálogo); upload de mídia roda fora da transação em melhor esforço — falha isolada de mídia não desfaz a publicação, só fica pendente até uma sincronização trazer o arquivo.
- Q: Decisões de moderação concorrentes ou submissão duplicada da mesma correção — qual estado final é garantido? → A: A primeira decisão vence; a sugestão é travada dentro da transação de decisão e uma segunda tentativa concorrente falha sem sobrescrever o status terminal já gravado; submissão duplicada/vazia da mesma correção é rejeitada no servidor antes de virar sugestão nova.
- Q: Quais recursos e critério objetivo delimitam a "renderização fiel" de FR-011 no MVP? → A: Campos, `FrontSide`, cloze, condicionais aninhadas, filtros `text`/`hint`/`type`, CSS e imagens, comparados por fixtures de conteúdo e estilos no Anki LTS; scripts e filtros personalizados ficam fora do MVP.
- Q: Sob quais condições objetivas devem ser medidos os 500ms de FR-054? → A: p95 de 20 medições após aquecimento, com 10 sessões concorrentes, dispositivo de 4 CPUs/8GB e rede de 100ms RTT/10Mbps, da ação até o conteúdo visível.
- Q: Como medir população, método e janela de SC-008 sem telemetria invasiva? → A: Durante 30 dias consecutivos da beta fechada, investigar 100% dos relatos de perda após sync comparando backup pré-sync e estado posterior; nenhuma perda confirmada de campo/tag protegida.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cadastro, login e consentimentos (Priority: P1)

Como estudante, quero me cadastrar e fazer login na plataforma web para poder acessar e assinar decks de forma segura, informando opcionalmente minha carreira alvo e banca/edital de interesse, e decidindo separadamente se aceito receber e-mails de novidades e se autorizo uso de dados anonimizados em pesquisa.

**Why this priority**: Nenhuma outra jornada é possível sem uma conta autenticada — é o pré-requisito de toda a plataforma.

**Independent Test**: Pode ser testado isoladamente criando uma conta nova, confirmando o e-mail, fazendo login, recuperando a senha e verificando que os dois consentimentos (e-mails e pesquisa) começam desmarcados e podem ser alterados depois.

**Acceptance Scenarios**:

1. **Given** um visitante sem conta, **When** ele se cadastra com e-mail e senha válidos, **Then** a conta é criada, a senha nunca é armazenada em texto puro, e um e-mail de verificação é enviado.
2. **Given** um usuário cadastrado, **When** ele informa credenciais corretas, **Then** ele recebe uma sessão autenticada válida para acessar áreas restritas da plataforma.
3. **Given** um usuário que esqueceu a senha, **When** ele solicita recuperação, **Then** ele consegue redefinir a senha por um canal seguro (e-mail).
4. **Given** o formulário de cadastro, **When** o usuário não marca as caixas de consentimento para e-mails de novidades e uso de dados em pesquisa, **Then** o cadastro é concluído normalmente e ambos os consentimentos ficam registrados como recusados (nunca pré-marcados).
5. **Given** um novo cadastro, **When** o usuário opcionalmente informa carreira alvo (Fiscal/Policial/Jurídica/Outra) e banca/edital de interesse, **Then** essas informações ficam salvas no perfil para uso posterior na recomendação de decks (User Story 2).

---

### User Story 2 - Exploração e assinatura do catálogo de decks (Priority: P1)

Como estudante, quero navegar pelo catálogo de decks com estatísticas e tags de matéria, encontrar rapidamente material relevante ao meu edital e me inscrever em um deck, para começar a recebê-lo no meu Anki local.

**Why this priority**: É a jornada de descoberta que conecta o usuário recém-cadastrado ao valor central do produto (ter acesso a material de estudo mantido pela comunidade).

**Independent Test**: Pode ser testado isoladamente navegando o catálogo, aplicando um filtro de matéria, e clicando em "Inscrever-se" em um deck, verificando que o vínculo usuário↔deck é criado.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado, **When** ele abre o catálogo, **Then** vê uma listagem paginada de decks com nome, matéria/tags, número de notas e número de assinantes.
2. **Given** o catálogo carregado, **When** o usuário aplica um filtro por tag/matéria, **Then** apenas os decks correspondentes são exibidos.
3. **Given** um usuário que informou carreira/banca no cadastro (User Story 1), **When** ele abre o catálogo, **Then** decks recomendados com base nessas informações aparecem no topo da listagem.
4. **Given** um usuário que não informou carreira/banca, **When** ele abre o catálogo, **Then** a listagem usa o comportamento padrão (mais assinantes/mais recentes).
5. **Given** um deck no catálogo, **When** o usuário clica em "Inscrever-se", **Then** o vínculo de assinatura é criado e o deck passa a ser elegível para sincronização (User Story 3).
6. **Given** um deck já assinado, **When** o usuário opta por cancelar a inscrição, **Then** o vínculo é removido e o deck deixa de ser sincronizado.

---

### User Story 3 - Sincronização do deck local via add-on (Priority: P1)

Como estudante, quero que o deck que assinei na web seja recebido e mantido atualizado automaticamente no meu Anki local, para não precisar buscar atualizações manualmente nem perder minhas anotações pessoais.

**Why this priority**: É a entrega concreta da proposta de valor do produto ("decks sempre atualizados no seu Anki") e o motivo técnico central de existir um add-on.

**Independent Test**: Pode ser testado isoladamente assinando um deck, dessincronizando/alterando uma nota na base oficial, disparando a sincronização (manual, ao abrir o Anki, ou encadeada ao sync nativo) e confirmando que a mudança chega ao Anki local sem afetar conteúdo protegido nem disparar sincronizações concorrentes.

**Acceptance Scenarios**:

1. **Given** um deck assinado, **When** o usuário aciona a sincronização manualmente pelo add-on, **Then** as notas novas/atualizadas/removidas desde a última sincronização são aplicadas localmente.
2. **Given** a opção de sincronização automática ativada, **When** o usuário abre o Anki, **Then** a sincronização com a plataforma ocorre sem ação manual.
3. **Given** a opção de sincronização encadeada ativada, **When** o usuário clica no botão de sincronização nativo do Anki, **Then** a sincronização com a plataforma ocorre primeiro e só depois o sync nativo do Anki prossegue.
4. **Given** uma sincronização em andamento, **When** o usuário tenta disparar outra sincronização antes de 10 segundos terem passado, **Then** a segunda tentativa é bloqueada até o intervalo mínimo de 10 segundos passar.
5. **Given** uma sincronização prestes a aplicar mudanças, **When** o add-on inicia o processo, **Then** um backup automático da coleção do Anki é criado antes de qualquer alteração.
6. **Given** um deck com alterações pendentes, **When** a sincronização roda, **Then** apenas o delta desde a última sincronização é aplicado (comparado ao cache local por nota), na ordem: tipos de nota → notas → reorganização de subdecks.
7. **Given** uma mudança estrutural grande demais para reconciliar via delta (ex.: número de templates do tipo de nota mudou), **When** a sincronização detecta esse caso, **Then** o add-on força uma ressincronização completa do deck em vez de aplicar o delta parcialmente.
8. **Given** notas com imagens em campos, **When** a sincronização ocorre, **Then** as imagens são sincronizadas e um arquivo já existente e inalterado (mesmo hash) não é reenviado/rebaixado.
9. **Given** uma nota removida oficialmente após aceite de sugestão de exclusão (User Story 9), **When** a mudança chega via sincronização, **Then** o comportamento local segue a preferência do assinante: apagar a nota de fato ou apenas marcá-la preservando o histórico de repetição espaçada.
10. **Given** uma sincronização interrompida no meio (ex.: queda de rede ou fechamento do Anki), **When** o add-on detecta a falha, **Then** a coleção é revertida para o backup criado antes da sincronização e uma nova tentativa completa é exigida — não há retomada parcial do delta interrompido.

---

### User Story 4 - Sugestão de mudança em nota existente (Priority: P1)

Como estudante, quero sugerir uma correção em uma nota já publicada, para contribuir com a qualidade do deck sem precisar de permissão de edição direta.

**Why this priority**: É o mecanismo central que resolve o problema descrito no PRD — decks que ficam desatualizados sem canal de correção. Sem essa jornada, o produto não entrega diferencial nenhum sobre compartilhar arquivos estáticos.

**Independent Test**: Pode ser testado isoladamente abrindo uma nota de um deck assinado, preenchendo tipo de mudança e justificativa, editando um campo pelo editor rich text, e confirmando que a sugestão aparece com status "pendente" vinculada ao autor, à nota e aos campos alterados.

**Acceptance Scenarios**:

1. **Given** uma nota de um deck assinado, **When** o usuário propõe uma mudança, **Then** ele deve escolher um tipo de mudança dentre categorias estruturadas (Conteúdo atualizado, Ortografia/Gramática, Erro de conteúdo, Nova tag, Tag atualizada, Outro) e preencher uma justificativa obrigatória.
2. **Given** o formulário de sugestão, **When** o usuário edita um campo, **Then** ele usa um editor de texto rico (WYSIWYG) com barra de formatação (negrito, itálico, sublinhado, tachado, listas, alinhamento, links, tamanho de fonte) e pode alternar para editar o HTML bruto diretamente.
3. **Given** uma sugestão preenchida, **When** o usuário revisa antes de enviar, **Then** ele vê um diff visual lado a lado ("Atual" vs. "Sugerido") por campo, com opção de expandir campos/tags que não mudaram.
4. **Given** uma sugestão enviada, **When** ela é registrada, **Then** fica com status "pendente", vinculada ao autor, à nota e ao(s) campo(s) alterado(s).
5. **Given** múltiplas notas selecionadas com a mesma correção (ex.: uma tag errada em 50 notas), **When** o usuário envia uma sugestão em lote, **Then** uma única sugestão é criada vinculada a todas as notas selecionadas, evitando múltiplas aprovações idênticas.

---

### User Story 5 - Tela de Community Suggestions e decisão de moderação (Priority: P1)

Como estudante ou moderador, quero ver todas as sugestões de um deck em um só lugar, opinar com curtidas/descurtidas e discussão, e — se eu for moderador — aceitar ou rejeitar cada uma, para manter a base oficial do deck sob controle de qualidade com apoio do sinal da comunidade.

**Why this priority**: Fecha o ciclo de valor iniciado pela User Story 4 — sem visibilidade e decisão, uma sugestão nunca vira melhoria real no deck nem se propaga aos assinantes.

**Independent Test**: Pode ser testado isoladamente abrindo a tela de um deck com sugestões pendentes, filtrando por status/autor/período, curtindo uma sugestão de terceiro, comentando na thread da sugestão e, como moderador, aceitando uma sugestão e confirmando que a nota oficial é atualizada e a rejeição informa o motivo ao autor.

**Acceptance Scenarios**:

1. **Given** um deck com sugestões, **When** qualquer assinante autenticado abre a tela de Community Suggestions, **Then** ele vê três abas — "Sugestões de mudança", "Sugestões de nota nova" e "Sugestões de exclusão" — mesmo sem ser moderador.
2. **Given** a tela de sugestões, **When** o usuário busca por ID de nota ou autor, ou filtra por status/período/tipo de envio, **Then** a lista é restringida de acordo.
3. **Given** uma sugestão listada, **When** o usuário a visualiza, **Then** vê autor, data, tipo de mudança, justificativa, diff (ou campos propostos) e a nota relacionada com contador de sugestões abertas.
4. **Given** uma sugestão de terceiro, **When** um assinante autenticado curte ou descurte, **Then** o sinal fica visível a todos, inclusive ao moderador, antes da decisão.
5. **Given** uma sugestão específica, **When** um usuário comenta nela, **Then** o comentário aparece na thread própria dessa sugestão, distinta da thread geral da nota (User Story 7).
6. **Given** um moderador do deck, **When** ele abre a tela de Community Suggestions, **Then** vê adicionalmente os botões de aceitar/rejeitar em cada sugestão.
7. **Given** uma sugestão pendente, **When** o moderador aceita, **Then** a mudança é aplicada na nota oficial (ou a nota é criada/removida, conforme o tipo), a sugestão é marcada como "aceita", e a mudança entra na fila de sincronização para todos os assinantes.
8. **Given** uma sugestão pendente, **When** o moderador rejeita, **Then** ela é marcada como "rejeitada" com motivo opcional visível ao autor da sugestão.
9. **Given** uma decisão já tomada, **When** qualquer usuário tenta desfazê-la pela interface, **Then** isso não é possível no MVP — reverter exige uma nova sugestão.

---

### User Story 6 - Inspeção e busca de notas (Priority: P2)

Como estudante, quero buscar notas por termo ou ID dentro de um deck, para localizar rapidamente o cartão que quero revisar ou discutir.

**Why this priority**: Melhora a usabilidade das jornadas centrais (sugerir, discutir), mas o produto ainda entrega valor sem busca refinada — o usuário pode navegar a listagem manualmente no curto prazo.

**Independent Test**: Pode ser testado isoladamente buscando um termo presente em um campo de nota e por um ID exato, dentro de um deck assinado, e conferindo que o resultado aparece rapidamente e a nota é renderizada fielmente ao template/CSS original do Anki.

**Acceptance Scenarios**:

1. **Given** um deck de até 10 mil notas, **When** o usuário busca por um termo presente em algum campo, **Then** o resultado aparece em menos de 500ms.
2. **Given** um ID de nota conhecido, **When** o usuário busca por esse ID exato, **Then** a nota correspondente é encontrada diretamente.
3. **Given** uma nota encontrada, **When** ela é exibida na web, **Then** a renderização reproduz fielmente o template e o CSS usados no Anki original, sem interferência do estilo visual do restante da aplicação.

---

### User Story 7 - Discussão geral na nota (Priority: P2)

Como estudante, quero comentar publicamente em uma nota, para debater dúvidas de conteúdo com outros candidatos, independentemente de haver uma sugestão em aberto.

**Why this priority**: Fortalece o engajamento comunitário citado no PRD, mas não bloqueia o ciclo essencial de correção de conteúdo (User Stories 4-5).

**Independent Test**: Pode ser testado isoladamente comentando em uma nota, confirmando que autor e timestamp aparecem, e que o autor consegue editar/excluir o próprio comentário.

**Acceptance Scenarios**:

1. **Given** uma nota de um deck assinado, **When** o usuário publica um comentário, **Then** ele aparece na thread da nota em ordem cronológica, sem aninhamento profundo, com autor e timestamp visíveis.
2. **Given** um comentário próprio, **When** o autor opta por editar ou excluir, **Then** a ação é aplicada somente ao próprio comentário.
3. **Given** o comentário geral de uma nota, **When** comparado à thread de uma sugestão específica sobre a mesma nota (User Story 5), **Then** ambas as threads permanecem distintas e não se misturam.

---

### User Story 8 - Sugestão de nota nova (Priority: P2)

Como estudante, quero propor uma nota inteiramente nova dentro de um deck que já assino, para contribuir com conteúdo que ainda não existe no material.

**Why this priority**: Expande a cobertura de conteúdo do deck, mas depende do ciclo de moderação já entregue pelas User Stories 4-5 e não é essencial para demonstrar o valor central do produto.

**Independent Test**: Pode ser testado isoladamente preenchendo todos os campos do tipo de nota do deck com o editor rich text, informando justificativa e tags, e confirmando que a proposta aparece na aba própria de nota nova em Community Suggestions.

**Acceptance Scenarios**:

1. **Given** um deck assinado, **When** o usuário propõe uma nota nova, **Then** o formulário apresenta todos os campos do tipo de nota do deck (ex.: Frente, Verso, Extra), cada um com o editor rich text de User Story 4.
2. **Given** um campo deixado vazio no formulário, **When** a sugestão é revisada, **Then** o campo vazio é sinalizado como tal para quem revisa.
3. **Given** o formulário preenchido, **When** o usuário envia, **Then** justificativa e tags são obrigatórias, e a sugestão aparece na aba "Sugestões de nota nova" (User Story 5), separada das sugestões de mudança.

---

### User Story 9 - Sugestão de exclusão de nota (Priority: P2)

Como estudante, quero sugerir que uma nota seja removida do deck, para sinalizar conteúdo duplicado, desatualizado (ex.: lei revogada) ou incorreto que não dá para consertar com uma simples edição.

**Why this priority**: Trata um caso de qualidade de conteúdo menos frequente que correção/adição, mas necessário para manter decks juridicamente atualizados no nicho de concursos.

**Independent Test**: Pode ser testado isoladamente propondo a exclusão de uma nota com justificativa, aceitando-a como moderador, e confirmando que ela some da base oficial e se propaga na sincronização seguinte (User Story 3).

**Acceptance Scenarios**:

1. **Given** uma nota de um deck assinado, **When** o usuário sugere sua exclusão, **Then** uma justificativa é obrigatória e a sugestão aparece na aba "Sugestões de exclusão" (User Story 5), como categoria própria (não uma "mudança" de campo).
2. **Given** uma sugestão de exclusão aceita pelo moderador, **When** a decisão é aplicada, **Then** a nota é removida da base oficial e essa remoção é propagada aos assinantes na próxima sincronização.

---

### User Story 10 - Convite de co-moderador (Priority: P3)

Como moderador, quero convidar outro usuário para ser mantenedor do meu deck, para dividir a curadoria sem depender de uma única pessoa.

**Why this priority**: Importante para sustentabilidade de longo prazo dos decks mais populares, mas um deck com um único moderador já opera plenamente no MVP sem essa jornada.

**Independent Test**: Pode ser testado isoladamente convidando um usuário por e-mail/username, confirmando que ele precisa aceitar para assumir o papel, e verificando que qualquer moderador pode remover outro (exceto a si mesmo se for o único restante).

**Acceptance Scenarios**:

1. **Given** um moderador de um deck, **When** ele convida outro usuário por e-mail/username, **Then** o convidado só assume o papel de moderador após aceitar o convite.
2. **Given** um deck com múltiplos moderadores, **When** qualquer um deles atua, **Then** todos têm o mesmo nível de permissão (aceitar/rejeitar sugestões, editar metadados do deck), sem hierarquia entre eles.
3. **Given** um deck com múltiplos moderadores, **When** um moderador tenta remover outro, **Then** a remoção é permitida, exceto quando o alvo é o próprio usuário e ele é o único moderador restante do deck.

---

### User Story 11 - Proteção de campos e tags pessoais (Priority: P2)

Como estudante, quero marcar campos e tags específicos como "protegidos" em um deck que assino, para que a sincronização nunca apague anotações ou tags pessoais que eu adicionei localmente na nota.

**Why this priority**: Protege dados pessoais do usuário durante a sincronização (User Story 3); sem essa proteção, o risco de perda de anotações pessoais desestimula o uso contínuo do add-on, mas o ciclo central de sync/sugestão/moderação já funciona sem ela.

**Independent Test**: Pode ser testado isoladamente configurando um campo e uma tag como protegidos para um deck, adicionando a tag de proteção pontual a uma nota específica, disparando uma sincronização com mudança na web, e confirmando que o conteúdo protegido permanece intacto localmente.

**Acceptance Scenarios**:

1. **Given** um deck assinado, **When** o assinante configura campos e tags como protegidos (aplicando-se como padrão a todas as notas do deck), **Then** essa configuração é salva por usuário + deck.
2. **Given** uma nota específica, **When** o usuário adiciona a tag `AnkiHubBR_Protect::NomeDoCampo` diretamente no Anki (espaço no nome do campo vira `_`), **Then** aquele campo fica protegido somente naquela nota, sem precisar abrir a web.
3. **Given** conteúdo protegido (por configuração de deck ou por tag na nota), **When** um delta sincronizado é aplicado, **Then** o conteúdo protegido é preservado em vez de sobrescrito pela versão da web.
4. **Given** tags internas de outros add-ons (ex.: `leech`, `marked`), **When** uma sincronização ocorre, **Then** essas tags nunca são tocadas, protegidas ou não.
5. **Given** um campo ou tag sem proteção configurada, **When** uma sincronização ocorre, **Then** o comportamento padrão é "web sempre vence".

---

### User Story 12 - Gestão de conta e privacidade (LGPD) (Priority: P3)

Como estudante, quero gerenciar meus dados e preferências de conta, para ter controle sobre minhas informações pessoais conforme a LGPD.

**Why this priority**: Requisito legal e de confiança do usuário, mas não bloqueia a demonstração do valor central do produto (descoberta, sync, sugestão, moderação) — deve estar pronto antes do lançamento público, não necessariamente no primeiro incremento demonstrável.

**Independent Test**: Pode ser testado isoladamente alterando os consentimentos dados no cadastro a partir de "Minha conta", solicitando exportação dos próprios dados em JSON, e agendando exclusão de conta.

**Acceptance Scenarios**:

1. **Given** a tela "Minha conta", **When** o usuário altera um consentimento (e-mails de novidades ou uso de dados em pesquisa), **Then** a mudança tem efeito imediato.
2. **Given** um usuário que solicita exclusão de conta, **When** ele confirma o pedido, **Then** a exclusão definitiva é agendada para 7 dias corridos, permitindo desistência nesse período; após o prazo, dados pessoais são apagados e assinaturas/sugestões são anonimizadas.
3. **Given** um usuário autenticado, **When** ele solicita exportação dos próprios dados, **Then** recebe um arquivo legível (JSON) com nome, e-mail, sugestões e comentários.

---

### User Story 13 - Denúncia de conteúdo abusivo (Priority: P3)

Como estudante, quero denunciar um comentário ou mensagem de discussão abusiva, para que a plataforma possa revisar e remover conteúdo problemático.

**Why this priority**: Necessário para responsabilidade legal e saúde da comunidade antes do lançamento público, mas é um caminho secundário acionado apenas quando há abuso — não faz parte do fluxo principal de uso do produto.

**Independent Test**: Pode ser testado isoladamente denunciando um comentário com motivo em texto livre, confirmando que a denúncia fica registrada como "pendente" vinculada ao conteúdo, ao autor da denúncia e ao autor do conteúdo, e que a remoção pelo administrador dispara notificação por e-mail ao autor do conteúdo removido.

**Acceptance Scenarios**:

1. **Given** um comentário (User Story 7) ou uma mensagem de discussão de sugestão (User Story 5), **When** um usuário clica em "Denunciar" e opcionalmente informa um motivo, **Then** a denúncia é registrada com status "pendente".
2. **Given** uma fila de denúncias pendentes, **When** um administrador da plataforma revisa e decide remover o conteúdo, **Then** o conteúdo é removido e, se necessário, a conta do autor pode ser suspensa (soft-ban reversível: sem login, comentário ou sugestão enquanto suspensa).
3. **Given** um conteúdo removido por denúncia, **When** a remoção é efetivada, **Then** o autor do conteúdo removido recebe uma notificação por e-mail informando o motivo.

---

### User Story 14 - Menu Revizza no menubar do Anki (Priority: P2)

Como estudante, quero acessar todas as funções do add-on por um menu "Revizza" próprio no menubar do Anki, já conectado ao servidor correto, para fazer login, sincronizar, gerenciar meus decks inscritos e publicar um deck sem configurar nada manualmente.

**Why this priority**: Melhora decisivamente a usabilidade das jornadas já entregues (US3 sync, publicação inicial), espelhando a UX consagrada do add-on AnkiHub original (Constituição, Princípio I); mas o ciclo central já funciona pelos itens em Ferramentas, então não bloqueia o MVP.

**Independent Test**: Pode ser testado isoladamente abrindo o Anki com o add-on instalado e verificando que o menu "Revizza" aparece no menubar (fora de Ferramentas) com os cinco itens do núcleo, que o login exige apenas e-mail/senha (sem URL), que "Testar conexão" reporta os dois sinais, e que "Decks inscritos" lista, permite cancelar inscrição e ajustar as preferências de sincronização do deck.

**Acceptance Scenarios**:

1. **Given** o Anki aberto com o add-on instalado, **When** o usuário olha o menubar, **Then** existe um menu top-level "Revizza" (não dentro de Ferramentas) com os itens: Entrar/Sair, Sincronizar agora, Decks inscritos, Criar deck Revizza, Testar conexão — sem um item "Preferências" separado, pois as preferências de sincronização por deck vivem dentro de "Decks inscritos".
2. **Given** um usuário não logado, **When** ele abre o menu Revizza, **Then** as ações que exigem autenticação (Sincronizar, Decks inscritos, Criar deck) aparecem desabilitadas, e Entrar e Testar conexão permanecem habilitadas.
3. **Given** o diálogo de login, **When** o usuário o abre, **Then** apenas e-mail e senha são solicitados — nenhum campo de URL da API, URL do Supabase ou chave pública é exibido ou exigido (as credenciais de conexão de produção vêm embutidas no pacote).
4. **Given** o item "Testar conexão", **When** acionado, **Then** o add-on reporta dois sinais distintos: alcance da API (endpoint público leve, sem auth) e validade da sessão (quando houver login) — cada um com resultado próprio.
5. **Given** o diálogo "Decks inscritos", **When** o usuário logado o abre, **Then** vê a lista dos decks que assina e pode, por deck, cancelar a inscrição, ajustar os gatilhos de sincronização (manual/automático/encadeado) e alterar a preferência de remoção (apagar vs marcar), sem sair do Anki; inscrever-se em deck novo continua sendo feito pela web.
6. **Given** o item "Criar deck Revizza", **When** acionado por um usuário logado, **Then** dispara o fluxo existente de importação inicial única (upload de deck inexistente), respeitando a resposta `409` quando o deck já foi publicado.

---

### Edge Cases

- O que acontece quando duas sincronizações do mesmo usuário são disparadas quase simultaneamente (manual + automática)? A segunda deve ser bloqueada pelo rate limit até a primeira concluir (User Story 3).
- O que acontece quando uma mudança estrutural no tipo de nota (ex.: número de templates) é grande demais para reconciliar via delta? O add-on deve forçar ressincronização completa do deck em vez de aplicar parcialmente (User Story 3).
- O que acontece quando um moderador tenta remover a si mesmo sendo o único moderador restante do deck? A remoção deve ser bloqueada — um deck nunca pode ficar sem moderador (User Story 10).
- O que acontece quando uma nota tem conteúdo protegido por tag e, ao mesmo tempo, uma sugestão para o mesmo campo é aceita na web? O conteúdo protegido localmente prevalece sobre a versão sincronizada (User Story 11).
- O que acontece quando o mesmo tipo de correção precisa ser aplicado a muitas notas de uma vez (ex.: tag errada em 50 notas)? Deve ser possível enviar como uma única sugestão em lote em vez de dezenas de sugestões individuais (User Story 4).
- O que acontece quando um usuário exclui a própria conta e depois muda de ideia dentro do prazo de 7 dias? A exclusão deve poder ser cancelada nesse período (User Story 12).
- O que acontece quando conteúdo HTML malicioso é submetido em um campo via editor rich text? Deve ser sanitizado antes de ser persistido ou exibido a outros usuários, sem afetar formatação legítima (User Story 4, User Story 8).
- O que acontece quando um usuário denunciado e suspenso (soft-ban) tenta comentar, sugerir ou logar? Todas essas ações devem ficar bloqueadas até a suspensão ser revertida (User Story 13).
- O que acontece quando uma sincronização é interrompida no meio (queda de rede, Anki fechado)? A coleção é revertida para o backup pré-sincronização e uma nova tentativa completa é exigida — não há retomada parcial (User Story 3).
- O que acontece quando o usuário roda o add-on em uma versão do Anki Desktop diferente da LTS mais recente? O MVP não garante compatibilidade fora da versão LTS mais recente (User Story 3).
- O que acontece quando a API está fora do ar e o usuário aciona "Testar conexão" ou uma sincronização? "Testar conexão" reporta falha de alcance da API com mensagem clara; a sincronização falha com erro legível, sem travar o Anki (User Story 14).
- O que acontece quando a sessão do usuário expira no add-on? "Testar conexão" reporta "API ok" e "Sessão expirada" como sinais distintos, orientando o usuário ao item Entrar (User Story 14).
- O que acontece quando uma dependência externa crítica (Supabase Auth/DB, e-mail, Storage) fica indisponível? O sistema retorna erro genérico e legível em pt-BR e reporta o incidente ao Sentry, sem retry automático nem modo degradado dedicado no MVP.
- O que acontece quando dois moderadores decidem (aceitar/rejeitar) a mesma sugestão quase simultaneamente? A primeira decisão prevalece; a segunda tentativa concorrente falha sem sobrescrever o status terminal já gravado (User Story 5).

## Requirements *(mandatory)*

### Functional Requirements

**Conta e acesso**
- **FR-001**: O sistema MUST permitir cadastro via e-mail/senha com verificação, armazenando a senha apenas de forma protegida (hash), nunca em texto puro.
- **FR-002**: O sistema MUST emitir uma sessão autenticada para usuários com credenciais válidas, para acesso a áreas restritas.
- **FR-003**: O sistema MUST oferecer recuperação de senha por um canal seguro.
- **FR-004**: O sistema MUST permitir, de forma opcional durante o cadastro, informar carreira alvo e banca/edital de interesse para uso em recomendações.
- **FR-005**: O sistema MUST solicitar dois consentimentos explícitos, separados e desmarcados por padrão no cadastro — recebimento de e-mails de novidades e uso de dados anonimizados em pesquisa. A alteração posterior desses consentimentos é coberta por FR-045.

**Catálogo e assinatura**
- **FR-006**: O sistema MUST exibir uma listagem paginada de decks com nome, matéria/tags, número de notas e número de assinantes.
- **FR-007**: O sistema MUST permitir filtrar o catálogo por tag/matéria.
- **FR-008**: O sistema MUST priorizar, no topo da listagem, decks recomendados com base na carreira/banca do usuário quando essa informação existir, e cair no critério padrão (mais assinantes/mais recentes) quando não existir.
- **FR-009**: O sistema MUST permitir que um usuário autenticado se inscreva e cancele a inscrição em um deck a qualquer momento.

**Notas e busca**
- **FR-010**: O sistema MUST permitir buscar notas dentro de um deck por termo textual nos campos ou por ID exato, retornando resultado em menos de 500ms para decks de até 10 mil notas.
- **FR-011**: O sistema MUST renderizar a nota na web reproduzindo o template e CSS originais do Anki para campos, `FrontSide`, cloze, condicionais aninhadas, filtros `text`/`hint`/`type` e imagens, isolado visualmente do CSS/tema do restante da aplicação. A fidelidade MUST ser validada comparando conteúdo e estilos de fixtures representativas no Anki LTS mais recente; scripts e filtros personalizados ficam fora do escopo do MVP.

**Discussão e sugestões**
- **FR-012**: O sistema MUST permitir comentários públicos em uma nota, em thread única cronológica (sem aninhamento profundo), com autor e timestamp visíveis, e permitir que o próprio autor edite ou exclua seu comentário.
- **FR-013**: O sistema MUST exigir, para toda sugestão de mudança em nota existente, um tipo de mudança estruturado (Conteúdo atualizado, Ortografia/Gramática, Erro de conteúdo, Nova tag, Tag atualizada, Outro) e uma justificativa obrigatória.
- **FR-014**: O sistema MUST fornecer, para edição de campos em sugestões (mudança ou nota nova), um editor de texto rico (WYSIWYG) que produza o mesmo HTML aceito pelos campos nativos do Anki, com opção de editar o HTML bruto diretamente.
- **FR-015**: O sistema MUST sanitizar todo HTML enviado pelo editor rich text antes de persistir ou exibir a outros usuários, removendo scripts e manipuladores de evento inline.
- **FR-016**: O sistema MUST exibir, para sugestões de mudança, um diff visual lado a lado ("Atual" vs. "Sugerido") por campo alterado.
- **FR-017**: O sistema MUST permitir sugestão em lote — mesmo tipo de mudança e justificativa aplicados a várias notas selecionadas em uma única submissão.
- **FR-018**: O sistema MUST permitir propor uma nota inteiramente nova em um deck assinado, apresentando todos os campos do tipo de nota do deck com o mesmo editor rich text, sinalizando campos deixados vazios, e exigindo justificativa e tags.
- **FR-019**: O sistema MUST permitir sugerir a exclusão de uma nota existente mediante justificativa obrigatória, tratando-a como categoria própria de sugestão.
- **FR-020**: O sistema MUST registrar toda sugestão (mudança, nota nova ou exclusão) com status inicial "pendente", vinculada ao autor, à(s) nota(s) e ao(s) campo(s) relevantes. Uma submissão duplicada ou vazia da mesma correção MUST ser rejeitada pelo servidor antes de virar uma nova sugestão.

**Community Suggestions e moderação**
- **FR-021**: O sistema MUST exibir, a qualquer assinante autenticado de um deck (não somente moderadores), uma tela com três abas — mudanças, notas novas e exclusões — listando todas as sugestões do deck.
- **FR-022**: O sistema MUST permitir buscar sugestões por ID de nota ou autor, e filtrar por status, período de criação e tipo de envio (individual/lote).
- **FR-023**: O sistema MUST permitir que qualquer assinante autenticado curta ou descurta uma sugestão de terceiro, com o resultado visível a todos.
- **FR-024**: O sistema MUST fornecer, para cada sugestão, uma thread de discussão própria, distinta da thread geral de comentários da nota.
- **FR-025**: O sistema MUST exibir botões de aceitar/rejeitar apenas a moderadores do deck, na própria tela de Community Suggestions.
- **FR-026**: O sistema MUST, ao aceitar uma sugestão, aplicar a mudança na nota oficial (ou criar/remover a nota, conforme o tipo), marcar a sugestão como "aceita" e enfileirar a mudança para sincronização de todos os assinantes.
- **FR-027**: O sistema MUST, ao rejeitar uma sugestão, marcá-la como "rejeitada" com motivo opcional visível ao autor, sem oferecer reversão da decisão pela interface no MVP. Decisões concorrentes (aceitar/rejeitar) sobre a mesma sugestão MUST resultar na primeira decisão prevalecendo — a sugestão é travada durante a decisão, e uma segunda tentativa concorrente MUST falhar sem sobrescrever o status terminal já gravado.

**Moderadores de deck**
- **FR-028**: O sistema MUST permitir que um moderador convide outro usuário (por e-mail/username) para se tornar moderador do mesmo deck, exigindo aceite do convidado antes de conceder o papel.
- **FR-029**: O sistema MUST tratar todos os moderadores de um deck com o mesmo nível de permissão, sem hierarquia entre eles.
- **FR-030**: O sistema MUST impedir que o único moderador restante de um deck remova a si mesmo, garantindo que um deck nunca fique sem moderador.

**Sincronização (add-on)**
- **FR-031**: O sistema MUST sincronizar deltas de deck (notas criadas/atualizadas/removidas) para o Anki local do assinante, sob três gatilhos configuráveis: manual, automático ao abrir o Anki, e encadeado antes do sync nativo do Anki.
- **FR-032**: O sistema MUST bloquear sincronizações concorrentes do mesmo usuário, permitindo no máximo uma a cada 10 segundos.
- **FR-033**: O sistema MUST criar um backup automático da coleção do Anki local antes de aplicar qualquer atualização vinda da sincronização.
- **FR-034**: O sistema MUST manter um registro local do estado da última sincronização por nota (identificador, timestamp/hash de modificação, tipo da última atualização) e aplicar apenas o delta desde então, na ordem: tipos de nota → notas → reorganização de subdecks.
- **FR-035**: O sistema MUST forçar uma ressincronização completa do deck quando uma mudança estrutural (ex.: alteração no número de templates de um tipo de nota) não puder ser reconciliada com segurança via delta parcial.
- **FR-036**: O sistema MUST sincronizar imagens referenciadas nos campos das notas, evitando reenviar/rebaixar um arquivo cujo conteúdo (hash) não mudou.
- **FR-037**: O sistema MUST propagar a remoção de uma nota (por sugestão de exclusão aceita) na sincronização seguinte, respeitando a preferência do assinante entre apagar a nota de fato ou apenas marcá-la preservando o histórico de repetição espaçada local.
- **FR-038**: O sistema MUST oferecer suporte apenas à versão LTS (Long Term Support) mais recente do Anki Desktop no MVP, sem garantir compatibilidade com versões não-LTS.
- **FR-039**: O sistema MUST, ao detectar falha ou interrupção durante uma sincronização (ex.: queda de rede, fechamento do Anki), reverter a coleção local para o backup criado antes da sincronização (FR-033) e exigir uma nova tentativa completa em vez de retomar ou deixar o delta parcialmente aplicado.
- **FR-062**: A importação inicial de um deck (criador autenticado, deck ainda inexistente — Constitution II) MUST persistir deck, tipo(s) de nota e notas em uma única transação atômica, de forma que o deck nunca apareça parcialmente publicado no catálogo; o upload da mídia associada MUST ocorrer em melhor esforço fora dessa transação — uma falha isolada de mídia não desfaz a publicação, permanecendo pendente até uma sincronização subsequente trazer o arquivo.

**Proteção de dados pessoais na sincronização**
- **FR-040**: O sistema MUST permitir que um assinante configure, por deck, uma lista de campos e de tags como "protegidos" (por correspondência de texto), aplicável por padrão a todas as notas do deck.
- **FR-041**: O sistema MUST permitir proteção pontual por nota via tag específica adicionada diretamente no Anki (convenção `AnkiHubBR_Protect::NomeDoCampo`), sem exigir acesso à web.
- **FR-042**: O sistema MUST preservar, ao aplicar um delta sincronizado, todo conteúdo protegido (por configuração de deck ou por tag na nota) em vez de sobrescrevê-lo com a versão da web.
- **FR-043**: O sistema MUST nunca alterar tags internas de outros add-ons (ex.: `leech`, `marked`) durante a sincronização, protegidas ou não.
- **FR-044**: O sistema MUST aplicar, na ausência de proteção configurada, o comportamento padrão de a versão da web sempre prevalecer.

**Conta, privacidade e moderação de conteúdo**
- **FR-045**: O sistema MUST permitir que o usuário revise e altere, a qualquer momento pela tela "Minha conta", os consentimentos dados no cadastro (e-mails de novidades e uso de dados em pesquisa), com efeito imediato.
- **FR-046**: O sistema MUST agendar a exclusão definitiva da conta para 7 dias corridos após a solicitação, permitindo desistência nesse período; decorrido o prazo, dados pessoais são apagados e assinaturas/sugestões do usuário são anonimizadas. O job de exclusão MUST ser idempotente, reexecutando na próxima janela agendada em caso de falha até concluir.
- **FR-047**: O sistema MUST permitir a exportação, sob solicitação, dos próprios dados do usuário (nome, e-mail, sugestões, comentários) em formato legível (JSON).
- **FR-048**: O sistema MUST permitir denunciar qualquer comentário ou mensagem de discussão de sugestão, com motivo opcional em texto livre, registrando a denúncia como "pendente" vinculada ao conteúdo, ao autor da denúncia e ao autor do conteúdo.
- **FR-049**: O sistema MUST permitir que um administrador da plataforma revise denúncias pendentes, remova o conteúdo denunciado e, se necessário, suspenda a conta do autor de forma reversível (soft-ban: sem login, comentário ou sugestão enquanto suspensa).
- **FR-050**: O sistema MUST notificar por e-mail o autor de um conteúdo removido por denúncia, informando o motivo; falha no envio do e-mail MUST NOT bloquear ou reverter a remoção do conteúdo.
- **FR-051**: O sistema MUST vincular toda sugestão, comentário e denúncia a um autor autenticado — não há submissão anônima no MVP.
- **FR-052**: O sistema MUST limitar a taxa de submissão nos endpoints de sincronização (10s — FR-032) e de envio de sugestões (20 submissões por minuto por usuário), para evitar abuso ou sobrecarga.

**Não-funcionais / transversais**
- **FR-053**: Toda tela do MVP MUST ser funcional em viewport de 360px de largura sem exigir rolagem horizontal (mobile-first).
- **FR-054**: Transições de página e renderização de preview de nota MUST atingir p95 de até 500ms em 20 medições após uma execução de aquecimento, da ação do usuário até o conteúdo visível, com deck de até 10 mil notas, 10 sessões autenticadas concorrentes, dispositivo de referência com 4 CPUs/8GB e rede limitada a 100ms RTT/10Mbps.
- **FR-055**: Toda tela do MVP MUST atender requisitos básicos de acessibilidade: labels associados a todo campo de formulário, contraste de texto/fundo em nível AA (WCAG), e operação via teclado para todo componente interativo (editor rich text, abas, botões de curtir/descurtir/aceitar/rejeitar).
- **FR-056**: Toda interface do MVP (textos, rótulos, mensagens de erro, e-mails transacionais) MUST estar em português do Brasil (pt-BR) — não há suporte a outros idiomas no MVP.

**Add-on — interface e conectividade**
- **FR-057**: O add-on MUST expor um menu top-level "Revizza" no menubar do Anki (não dentro de Ferramentas/Tools), contendo exatamente os itens do núcleo: Entrar/Sair, Sincronizar agora, Decks inscritos, Criar deck Revizza e Testar conexão; itens que exigem autenticação ficam desabilitados enquanto não houver sessão.
- **FR-058**: O add-on MUST vir pré-configurado com as credenciais de conexão de produção (URL da API, URL do Supabase e chave pública do Supabase) embutidas como constantes do pacote, sem exibir nenhum desses campos na interface — o usuário só informa e-mail e senha; override é possível apenas pelo config.json avançado do Anki (uso de desenvolvimento/teste).
- **FR-059**: O add-on MUST oferecer a ação "Testar conexão", que verifica o alcance da API por um endpoint público leve (sem autenticação) e, quando houver sessão, valida também o token — reportando dois sinais distintos ("API ok" e "Sessão ok/expirada") com mensagens legíveis.
- **FR-060**: O add-on MUST fornecer um diálogo "Decks inscritos" — único ponto de gestão por-deck do add-on, absorvendo as preferências de gatilho de sincronização (manual/automático/encadeado — FR-031) — que lista os decks assinados do usuário e permite cancelar a inscrição e alterar a preferência de remoção de nota (apagar vs marcar — FR-037) diretamente no Anki; a inscrição em novos decks permanece exclusiva da plataforma web (FR-009).
- **FR-061**: Todo o copy visível do add-on (menu, diálogos, mensagens) MUST usar a marca "Revizza"; a convenção de tag de proteção `AnkiHubBR_Protect::<Campo>` (FR-041) permanece inalterada por compatibilidade com dados já existentes.

### Key Entities *(include if feature involves data)*

- **Usuário**: conta de estudante com e-mail, senha (protegida), sessão autenticada, preferências opcionais de carreira/banca, e consentimentos LGPD (e-mails de novidades, uso de dados em pesquisa).
- **Papel de Moderador**: relação entre um usuário e um deck específico que concede permissão de aceitar/rejeitar sugestões e editar metadados do deck; um deck pode ter vários moderadores, todos com o mesmo nível de permissão.
- **Administrador da plataforma**: papel interno (não modelado como persona de produto) responsável por revisar denúncias em qualquer deck via painel administrativo.
- **Deck**: coleção publicada de notas com nome, matéria/tags, contagem de notas e de assinantes, e um ou mais moderadores.
- **Tipo de Nota**: define os campos (ex.: Frente, Verso, Extra) e os templates de renderização de um deck; mudanças estruturais nele (ex.: número de templates) podem exigir ressincronização completa.
- **Nota**: unidade de conteúdo dentro de um deck, com valores de campo (HTML sanitizado) e tags, alvo de comentários, sugestões e buscas.
- **Assinatura**: vínculo usuário↔deck que habilita a sincronização e é criado/removido pelo próprio usuário.
- **Sugestão**: proposta de mudança, nota nova ou exclusão, vinculada a autor, nota(s)-alvo (individual ou em lote), tipo/justificativa, status (pendente/aceita/rejeitada), curtidas/descurtidas, e thread de discussão própria.
- **Comentário**: mensagem pública com autor e timestamp, vinculada a uma nota (thread geral) ou a uma sugestão (thread da sugestão) — as duas threads nunca se misturam.
- **Denúncia**: registro vinculado a um conteúdo denunciado (comentário ou mensagem de discussão), ao autor da denúncia e ao autor do conteúdo, com status (pendente/revisada).
- **Configuração de Proteção**: lista de campos/tags marcados como protegidos por um usuário para um deck (aplicação padrão a todas as notas), mais a proteção pontual por nota via tag `AnkiHubBR_Protect::<Campo>`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nos primeiros 3 meses após o lançamento, a plataforma atinge 500 usuários cadastrados e 20 decks publicados (baseline provisório, sujeito a revisão — ver Assumptions).
- **SC-002**: Ao menos 40% dos usuários inscritos em algum deck realizam pelo menos 1 sincronização via add-on por semana.
- **SC-003**: A comunidade envia ao menos 100 sugestões de mudança por mês, com taxa de aceite pelos moderadores de ao menos 30%.
- **SC-004**: Ao menos 25% dos usuários cadastrados no primeiro mês seguem sincronizando ativamente no terceiro mês.
- **SC-005**: Usuários conseguem localizar uma nota específica dentro de um deck de até 10 mil notas (por termo ou ID) em menos de 500ms.
- **SC-006**: Usuários conseguem concluir cadastro e primeiro login em menos de 2 minutos, sem assistência externa.
- **SC-007**: Todas as telas do MVP permanecem utilizáveis (sem rolagem horizontal) em uma tela de 360px de largura.
- **SC-008**: Durante 30 dias consecutivos da beta fechada, 100% dos relatos de perda após sincronização feitos pelos participantes MUST ser investigado comparando o backup pré-sync com o estado posterior; nenhum relato pode confirmar perda de anotação, campo ou tag pessoal protegida pelo usuário.
- **SC-009**: Toda tela do MVP passa em auditoria de contraste AA (WCAG) e permite completar cada fluxo crítico (cadastro, inscrição, sugestão, moderação) usando somente o teclado.

## Assumptions

- As metas numéricas de SC-001 a SC-004 são os valores sugeridos como baseline pelo próprio PRD (marcados `TBD-valor`); nenhuma meta foi validada previamente pelo usuário e devem ser recalibradas com dados reais dos primeiros 3 meses.
- Autenticação usa um provedor gerenciado de sessão/token (mecanismo específico é decisão de plano/implementação, não de escopo funcional).
- Decks são sempre públicos no MVP — não há decks privados ou grupos fechados por convite (fora de escopo, ver PRD §2.3).
- A sincronização é sempre unidirecional (web → Anki local); o add-on nunca envia edições locais de volta à plataforma no MVP — toda contribuição de conteúdo passa pelo fluxo de sugestão (User Stories 4, 8, 9).
- Apenas imagens são sincronizadas como mídia no MVP; áudio/vídeo embutido além do que o Anki já trata nativamente está fora de escopo.
- Recursos de geração/avaliação por IA (busca inteligente, chatbot de estudo) estão fora de escopo do MVP e não são cobertos por esta especificação.
- Não há monetização, planos pagos ou cobrança no MVP.
- Não há aplicativo mobile nativo — a resposta à necessidade mobile é a responsividade mobile-first da web (FR-053).
- Não há histórico de versões navegável nem rollback de decisões de moderação pela interface no MVP (FR-027).
- A migração inicial de decks para a plataforma é manual, feita pelo próprio criador via add-on — não há importação automática de fontes externas (Google Drive, Telegram).
