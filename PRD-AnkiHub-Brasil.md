# PRD — AnkiHub Brasil

**Status:** Rascunho para revisão
**Versão:** 1.5 (adicionada arquitetura e empacotamento do add-on, seção 4.6)
**Data:** 2026-07-12
**Idioma:** Português (Brasil)

---

## 1. Sumário Executivo

**Problema:** Concurseiros brasileiros dependem do Anki para memorização de longo prazo, mas o compartilhamento de decks hoje é fragmentado (Google Drive, Telegram, WhatsApp) e estático — quando uma lei ou entendimento jurisprudencial muda, os cartões já distribuídos ficam obsoletos e não há canal para corrigi-los ou para debater seu conteúdo.

**Solução proposta:** Uma plataforma web colaborativa — o "AnkiHub Brasil" — que centraliza a publicação de decks, permite que a comunidade discuta e sugira correções nota a nota, e sincroniza atualizações em tempo real com o Anki local dos usuários por meio de um add-on nativo.

**Critérios de sucesso (KPIs do MVP):**

> Nenhuma meta numérica foi validada previamente pelo usuário. Os valores abaixo são sugestões de partida (marcadas `TBD-valor`) para servirem de baseline nos primeiros 3 meses pós-lançamento; devem ser ajustados com dados reais assim que disponíveis.

- **Adoção:** `TBD-valor` (sugestão: 500 usuários cadastrados e 20 decks publicados) nos primeiros 3 meses.
- **Sincronização ativa:** `TBD-valor` (sugestão: ≥ 40%) dos usuários inscritos com ao menos 1 sincronização via add-on por semana.
- **Engajamento comunitário:** `TBD-valor` (sugestão: ≥ 100 sugestões de mudança enviadas/mês) e taxa de aceite pelos moderadores ≥ 30% (indica que as sugestões têm qualidade, não é ruído).
- **Retenção:** `TBD-valor` (sugestão: ≥ 25%) dos usuários cadastrados no mês 1 seguem sincronizando ativamente no mês 3.

---

## 2. Experiência do Usuário e Funcionalidades

### 2.1. Personas

| Persona | Descrição | Necessidade principal |
| --- | --- | --- |
| **Estudante (Usuário Padrão)** | Concurseiro preparando-se para carreiras Fiscal, Policial ou Jurídica | Material atualizado, confiável, e espaço para tirar dúvidas ponto a ponto |
| **Moderador (Mantenedor do Deck)** | Autor ou um dos responsáveis por um deck publicado na plataforma — um deck pode ter mais de um moderador com o mesmo nível de permissão | Controle de qualidade sobre o conteúdo do seu deck, sem perder a colaboração da comunidade, e poder dividir a curadoria com outros mantenedores de confiança |

> Papel adicional (não modelado como persona de produto): **Administrador da plataforma** — equipe interna com acesso ao painel Django admin, responsável por revisar denúncias de conteúdo (US-14) em qualquer deck. Não tem tela dedicada no MVP.

### 2.2. User Stories e Critérios de Aceite

**US-01 — Cadastro e login**
Como estudante, quero me cadastrar e fazer login na plataforma web, para que eu possa acessar e assinar decks de forma segura.
- AC: Cadastro via e-mail/senha com verificação; senhas armazenadas com hash (nunca em texto puro).
- AC: Sessão autenticada via token (JWT ou equivalente do provedor de auth escolhido).
- AC: Recuperação de senha disponível.
- AC: Onboarding curto e opcional coleta carreira alvo (Fiscal/Policial/Jurídica/Outra) e banca ou edital de interesse, usados para recomendar decks (ver US-02).
- AC: Consentimento explícito e separado (não pré-marcado) para (a) receber e-mails de novidades/produto e (b) uso de dados anonimizados para pesquisa — ambos opcionais e reversíveis depois em "Minha conta" (ver US-13), conforme LGPD.

**US-02 — Exploração do catálogo**
Como estudante, quero navegar pelo catálogo de decks com estatísticas e tags de matéria, para encontrar rapidamente material relevante ao meu edital.
- AC: Listagem paginada de decks com nome, matéria/tags, nº de notas e nº de assinantes.
- AC: Filtro por tag/matéria.
- AC: Decks recomendados no topo da listagem com base na carreira/banca informada no onboarding (US-01), quando disponível; sem isso, cai no comportamento padrão (mais assinantes/mais recentes).

**US-03 — Inspeção de notas**
Como estudante, quero buscar notas por termo ou ID dentro de um deck, para localizar rapidamente o cartão que quero revisar ou discutir.
- AC: Busca textual nos campos das notas e por ID exato, com resultado em < 500ms para decks de até 10 mil notas (ver RNF-002).
- AC: Nota renderizada na web reproduz fielmente o template/CSS do Anki original (ver RF-005).

**US-04 — Discussão comunitária**
Como estudante, quero comentar publicamente em uma nota, para debater dúvidas de conteúdo com outros candidatos.
- AC: Comentários em thread simples (sem aninhamento profundo no MVP), ordenados cronologicamente.
- AC: Autor do comentário e timestamp visíveis; autor pode editar/excluir o próprio comentário.
- AC: Este comentário é sobre o conteúdo da nota em geral — é uma thread distinta da discussão vinculada a uma sugestão específica (ver US-09).

**US-05 — Sugestão de mudança em nota existente**
Como estudante, quero sugerir uma correção em uma nota já publicada, para contribuir com a qualidade do deck sem precisar de permissão de edição direta.
- AC: Campo obrigatório "Tipo de mudança", com categorias estruturadas: `Conteúdo atualizado`, `Ortografia/Gramática`, `Erro de conteúdo`, `Nova tag`, `Tag atualizada`, `Outro` (referência: campo `Type of change` do AnkiHub original).
- AC: Campo obrigatório "Justificativa da mudança" (texto livre) — no nosso nicho, orientar o usuário a citar a fonte (lei, artigo, súmula, informativo) que embasa a correção.
- AC: Editor **rich text (WYSIWYG)** por campo do cartão — não Markdown: barra com formatação (negrito, itálico, sublinhado, tachado, listas, alinhamento, links, tamanho de fonte) que gera o mesmo HTML usado nos campos nativos do Anki, com opção "Mostrar código-fonte" para editar o HTML bruto.
- AC: Sugestão registrada com status `pendente`, vinculada ao autor, à nota e ao(s) campo(s) alterado(s).
- AC: Diff visual lado a lado ("Atual" vs. "Sugerido") por campo, com opção de expandir campos e tags que não mudaram.
- AC: Suporte a **sugestão em lote**: o mesmo tipo de mudança e justificativa podem ser aplicados a várias notas selecionadas de uma vez (ex.: corrigir uma tag em 50 notas), gerando uma única sugestão vinculada a todas elas — evita que o moderador precise aprovar dezenas de itens idênticos um a um.

**US-06 — Sugestão de nota nova**
Como estudante, quero propor uma nota inteiramente nova dentro de um deck que já assino, para contribuir com conteúdo que ainda não existe no material.
- AC: Formulário apresenta todos os campos do tipo de nota do deck (ex.: Frente, Verso, Extra), cada um com o mesmo editor rich text de US-05; campo vazio é sinalizado como tal para quem revisa.
- AC: Exige "Justificativa" (por que essa nota deveria existir) e tags.
- AC: Aparece em aba própria na tela de Community Suggestions (ver US-09), separada das sugestões de mudança.

**US-07 — Sugestão de exclusão de nota**
Como estudante, quero sugerir que uma nota seja removida do deck, para sinalizar conteúdo duplicado, desatualizado (ex.: lei revogada) ou incorreto que não dá pra consertar com uma simples edição.
- AC: Requer justificativa obrigatória.
- AC: Tratada como uma categoria própria de sugestão (não uma "mudança" de campo) — aparece na aba de exclusões na tela de Community Suggestions.
- AC: Se aceita pelo moderador, a nota é removida da base oficial e a remoção é propagada aos assinantes na próxima sincronização.
- AC: O comportamento local ao aplicar essa remoção é configurável pelo assinante: apagar a nota do Anki de fato, ou apenas marcá-la (ex.: tag/estado) preservando o histórico de revisão local — réplica de uma opção real do AnkiHub original, útil porque apagar a nota também apaga o histórico de repetição espaçada dela.

**US-08 — Assinatura e sincronização**
Como estudante, quero me inscrever em um deck pela web e recebê-lo/atualizá-lo automaticamente no meu Anki local, para não precisar buscar atualizações manualmente.
- AC: Botão "Inscrever-se" no deck cria o vínculo usuário↔deck no backend.
- AC: Sincronização com a plataforma tem três gatilhos possíveis, configuráveis pelo usuário: (a) manual, via botão/menu dedicado do add-on; (b) automática ao abrir o Anki; (c) automática encadeada **antes** do sync nativo do Anki (AnkiWeb) — ou seja, ao clicar no botão de sync padrão do Anki, primeiro roda o sync com nossa plataforma e só depois o sync nativo continua. Réplica do comportamento real do AnkiHub, que intercepta a função de sync nativa do Anki para encadear a própria sincronização antes dela (não injeta dados no payload do AnkiWeb, só ordena as duas syncs em sequência).
- AC: Sincronizações concorrentes são bloqueadas (rate limit de uma sincronização a cada poucos segundos) para evitar corrupção do banco SQLite local por escritas simultâneas.
- AC: O add-on cria um **backup automático da coleção do Anki** antes de aplicar qualquer atualização vinda da sincronização, permitindo reverter manualmente se algo der errado.
- AC: O add-on mantém um cache local (tabela própria, por exemplo via SQLite/peewee) com o estado da última sincronização por nota (id, hash/timestamp de modificação, tipo da última atualização); ao sincronizar, identifica deltas comparando com esse cache e aplica apenas as mudanças (não repuxa o deck inteiro a cada vez).
- AC: Ordem de aplicação do delta: 1) tipos de nota (cria/renomeia, reordena campos preservando a ordem local e colocando campos novos no fim), 2) notas (cria/atualiza/remove), 3) reorganização em subdecks.
- AC: Se a mudança estrutural for grande demais para reconciliar via delta (ex.: número de templates do tipo de nota mudou), o add-on força uma **ressincronização completa do deck** em vez de tentar aplicar o delta parcialmente — evita corrupção silenciosa do note type local.
- AC: Imagens referenciadas nos campos são sincronizadas junto com as notas; cada arquivo é rastreado por hash de conteúdo no backend para evitar reenviar/rebaixar arquivo inalterado.
- AC: Usuário pode cancelar a inscrição a qualquer momento.

**US-09 — Tela de Community Suggestions**
Como estudante ou moderador, quero ver todas as sugestões de um deck em um só lugar — não só as minhas — para acompanhar o que a comunidade está propondo, opinar e ajudar a sinalizar qualidade antes da decisão do moderador.
- AC: Tela acessível a partir da página do deck, visível a **qualquer assinante** (não é uma fila privada do moderador).
- AC: Três abas: "Sugestões de mudança", "Sugestões de nota nova" e "Sugestões de exclusão" (US-05/06/07).
- AC: Busca por ID da nota ou autor, e filtros por status (aberta/fechada/aceita/rejeitada), período de criação e tipo de envio (individual/lote).
- AC: Cada sugestão mostra autor, data, tipo de mudança, justificativa, diff (ou campos propostos), e nota relacionada com contador de quantas sugestões abertas ela já tem.
- AC: Qualquer assinante autenticado pode curtir/descurtir (👍/👎) uma sugestão de terceiro — sinal de qualidade visível a todos, inclusive ao moderador, antes da decisão.
- AC: Cada sugestão tem sua própria thread de discussão (comentários específicos sobre aquela proposta), distinta do comentário geral da nota (US-04).
- AC: Moderadores do deck veem, adicionalmente, os botões de aceitar/rejeitar (US-10) diretamente nesta tela.

**US-10 — Decisão de moderação**
Como moderador, quero aceitar ou rejeitar uma sugestão a partir da tela de Community Suggestions, para manter a base oficial do deck sob controle de qualidade, usando o sinal de curtidas/descurtidas e a discussão da comunidade como apoio à decisão.
- AC: Aceitar aplica a mudança na nota oficial (ou cria/remove a nota, conforme o tipo) e marca a sugestão como `aceita`; a mudança entra na fila de sincronização para todos os assinantes.
- AC: Rejeitar marca como `rejeitada` com campo opcional de motivo, visível ao autor da sugestão.
- AC: Ação é irreversível via UI no MVP (reversão exigiria nova sugestão) — ver Não-Objetivos.

**US-11 — Convite de co-moderador**
Como moderador, quero convidar outro usuário para ser mantenedor do meu deck, para dividir a curadoria sem depender de uma única pessoa.
- AC: Convite por e-mail/username; convidado precisa aceitar para assumir o papel.
- AC: Todos os moderadores de um deck têm o mesmo nível de permissão no MVP (aceitar/rejeitar sugestões, editar metadados do deck); não há hierarquia entre eles.
- AC: Qualquer moderador pode remover outro moderador do deck, exceto a si mesmo se for o único restante (deck nunca fica sem moderador).

**US-12 — Proteção de campos e tags pessoais**
Como estudante, quero marcar campos e tags específicos como "protegidos" em um deck que assino, para que a sincronização nunca apague anotações ou tags pessoais que eu adicionei localmente na nota.
- AC: Configuração por deck, feita pelo assinante (não pelo moderador): lista de campos do tipo de nota (ex.: um campo "Notas pessoais") e lista de tags por correspondência de texto — aplica-se como padrão a todas as notas do deck.
- AC: Proteção pontual por nota via **convenção de tag** dentro do próprio Anki, sem precisar abrir a web: adicionar a tag `AnkiHubBR_Protect::NomeDoCampo` a uma nota protege aquele campo só naquela nota (espaço no nome do campo vira `_`); referência: é assim que o AnkiHub original implementa (tag `AnkiHub_Protect::<field>`).
- AC: Ao aplicar um delta sincronizado, o add-on preserva o conteúdo protegido (por configuração de deck ou por tag na nota) em vez de sobrescrevê-lo com a versão da web.
- AC: Tags internas de outros add-ons (ex.: `leech`, `marked`) nunca são tocadas pela sincronização, protegidas ou não.
- AC: Sem essa proteção configurada, o comportamento padrão continua sendo "web sempre vence" (ver Riscos Técnicos).

**US-13 — Gestão de conta e privacidade**
Como estudante, quero gerenciar meus dados e preferências de conta, para ter controle sobre minhas informações pessoais conforme a LGPD.
- AC: Tela "Minha conta" permite revisar/alterar os consentimentos dados no cadastro (e-mails de novidades, uso de dados em pesquisa) a qualquer momento, com efeito imediato.
- AC: Botão "Excluir conta" agenda a exclusão definitiva em 7 dias corridos (permitindo o usuário desistir nesse período); após o prazo, dados pessoais são apagados e assinaturas/sugestões do usuário são anonimizadas.
- AC: Usuário pode solicitar exportação dos próprios dados (nome, e-mail, sugestões, comentários) em formato legível (JSON), atendendo ao direito de portabilidade da LGPD.

**US-14 — Denúncia de conteúdo abusivo**
Como estudante, quero denunciar um comentário ou mensagem de discussão abusiva, para que a plataforma possa revisar e remover conteúdo problemático mesmo fora do escopo de um deck específico.
- AC: Botão "Denunciar" disponível em cada comentário (US-04) e em cada mensagem de discussão de sugestão (US-09), com motivo opcional em texto livre.
- AC: Denúncia registrada com status `pendente`, vinculada ao conteúdo denunciado, ao autor da denúncia e ao autor do conteúdo denunciado.
- AC: Fila de denúncias é revisada pela equipe da plataforma (papel de administrador global, distinto do moderador de deck) — no MVP, usar o painel administrativo nativo do Django em vez de construir uma tela dedicada.
- AC: Administrador pode remover o conteúdo denunciado e, se necessário, suspender a conta do autor (soft-ban reversível: usuário não consegue logar, comentar ou sugerir enquanto suspenso).
- AC: Autor do conteúdo removido recebe notificação por e-mail informando o motivo.

### 2.3. Não-Objetivos (fora do escopo do MVP)

- Edição colaborativa em tempo real (estilo Google Docs) dentro de uma nota.
- Permissões granulares por campo/tag ou hierarquia entre moderadores (ex.: "moderador-chefe" vs. "moderador júnior") — no MVP todo moderador de um deck tem o mesmo nível de permissão (ver US-11).
- Sistema de reputação/pontuação por sugestões aceitas ou votos recebidos — like/dislike (US-09) é só um sinal de qualidade para o moderador, não vira "score" público de usuário.
- Decks privados com convite exclusivo (grupos de estudo fechados) — MVP trabalha apenas com decks públicos comunitários; avaliar como funcionalidade futura fora deste roadmap.
- Optional Tag Groups (extensões de tags criadas por terceiros sobre um deck, ex.: tags por banca/edital) — planejado para v1.1 (ver Roadmap), não faz parte do MVP.
- Monetização, planos pagos ou cobrança — MVP é **totalmente gratuito** (decisão confirmada).
- Aplicativo mobile nativo — a resposta é responsividade *mobile-first* na web (RNF-001), não um app dedicado.
- Histórico de versões navegável / rollback de aceites de moderação.
- Suporte a decks com mídia pesada (áudio/vídeo embutido) além do que o Anki já trata nativamente — apenas imagens são sincronizadas no MVP (ver US-08). Controle granular (desabilitar download de mídia por deck/usuário) e otimização de cota de armazenamento ficam para v1.1+.
- Moderação automática de conteúdo (filtro de palavrões, IA de detecção de abuso) e apelação formal de banimento — no MVP, denúncias (US-14) são revisadas manualmente e contestação de banimento acontece por e-mail de suporte, não por um fluxo dedicado no produto.
- Importação automática de conteúdo de fontes externas (Google Drive, Telegram) — a migração inicial de decks é manual, feita pelo próprio criador via add-on.

---

## 3. Requisitos de IA

Não aplicável ao MVP — o produto não possui componente de geração ou avaliação por modelos de linguagem nesta fase.

Planejado para **v2.0+** (referência: recursos equivalentes já existem no AnkiHub original): busca inteligente de flashcards a partir de vídeo-aula/PDF ("Smart Search") e um assistente/chatbot de estudo para dúvidas de conteúdo. Quando esta fase for priorizada, esta seção deve ser expandida com requisitos de ferramentas, fontes de dados de treino/contexto e estratégia de avaliação (precisão das buscas, taxa de resposta útil do chatbot) antes do desenvolvimento.

---

## 4. Especificações Técnicas

### 4.1. Visão Geral da Arquitetura

```
[Anki Desktop + Add-on] <--HTTPS/API--> [Backend Django + DRF] <--> [SQL DB (Postgres via Supabase)]
                                               |        |
                                          [Auth: Supabase Auth]   [Mídia: Supabase Storage/S3]
                                               |
[Web App Next.js/React] <-----HTTPS/API-------+
```

- **Fluxo de publicação:** Moderador cria/importa deck via add-on → add-on faz upload inicial via API → backend persiste decks/notas/modelos no schema relacional. Um deck pode ter N moderadores (tabela de junção `deck_moderators`), todos com o mesmo nível de permissão (ver US-11).
- **Fluxo de assinatura:** Usuário clica "Inscrever-se" na web → backend registra vínculo usuário↔deck → ao rodar a sincronização própria do add-on (US-08), este consulta deltas pendentes desde o último `mod` registrado no cache local, verifica campos/tags protegidos (configurados no deck ou via tag na nota, US-12) e aplica localmente preservando o que estiver protegido — na ordem tipos de nota → notas → subdecks, com fallback para ressincronização completa quando o delta não é reconciliável com segurança.
- **Fluxo de sugestão → aceite → propagação:** Usuário sugere mudança/nota nova/exclusão na web (US-05/06/07) → sugestão fica `pendente` e visível a todos os assinantes na tela de Community Suggestions (US-09), que podem curtir/descurtir e discutir → moderador aceita (US-10) → nota oficial é criada/atualizada/removida → mudança entra na fila de sincronização → add-ons de todos os assinantes buscam o delta na próxima sincronização.

### 4.2. Pontos de Integração

- **API para o add-on Anki (RF-002):** endpoints REST (DRF) para upload inicial de deck, consulta de deltas por deck/timestamp, e download de atualizações. Autenticação via token vinculado à conta web do usuário. Segue as mesmas convenções observadas no AnkiHub original: rotas com barra final, paginação por cursor (campo `next`), e endpoints de sugestão em lote (`bulk-change-suggestions`) que aceitam alterações em várias notas em uma única submissão (ver US-05).
- **Autenticação (RF-001):** provedor gerenciado (ex.: Supabase Auth) para reduzir esforço de implementação própria de login/cadastro seguro.
- **Banco de dados (RF-005):** schema relacional mapeável 1:1 com as tabelas nativas do Anki (`notes`, `notetypes`/`models`, `templates`, `fields`, `cards`, `col` para CSS/config), garantindo que a reconstrução do `.apkg`/SQLite local a partir dos dados web seja determinística.
- **Proteção de dados pessoais (US-12):** tabelas `user_protected_fields` e `user_protected_tags`, vinculadas a usuário + deck, consultadas pelo add-on antes de sobrescrever uma nota local durante a sincronização.

### 4.3. Stack Tecnológica

- **Backend:** Python com **Django + Django REST Framework (DRF)** — decisão alinhada ao backend real do AnkiHub original (confirmado via padrões observados na API pública do add-on: paginação por cursor com campo `next`, rotas com barra final, versionamento de API via header `Accept`), o que reduz risco de reinventar padrões que o próprio nicho já validou. DRF resolve nativamente paginação, versionamento e serialização — menos código do que montar isso à mão em um framework mais minimalista.
- **Frontend:** React com Next.js (confirmado pelo usuário).
- **Banco de dados:** Postgres via Supabase, projeto criado na região **US East (Virginia)** — não em São Paulo — para ficar co-localizado com o backend no Heroku (ver abaixo); a autenticação segue via Supabase Auth em vez do `TokenAuthentication` nativo do DRF, para não abrir mão do custo-benefício de auth gerenciada já decidido.
- **Armazenamento de mídia:** Supabase Storage (compatível com S3, URLs pré-assinadas para upload/download) — mesmo padrão usado pelo AnkiHub original com S3 puro.
- **Add-on:** Python, usando as bibliotecas nativas do ecossistema Anki (`aqt`/`anki`), consistente com a stack de backend.
- **Hospedagem do backend (compute):** **Heroku**, decisão do ano 1 aproveitando créditos já disponíveis (cobre ~1 ano de dynos). Sem addon de Postgres do Heroku — o dyno conecta direto na connection string da Supabase (via Supavisor/pooler) pela variável `DATABASE_URL`. Heroku Common Runtime só tem região EUA/Europa (sem São Paulo), daí o banco também ficar nos EUA: co-localizar backend e banco reduz mais a latência do que aproximar o banco do usuário final, já que uma página pode disparar várias queries em sequência. Reavaliar para Railway/Render/Fly.io quando os créditos expirarem (custo deixa de ser zero: dyno Eco parte de ~$5/mês).
- **Observabilidade:** Sentry para rastreamento de erros (backend e add-on), mesma ferramenta usada pelo AnkiHub original.

### 4.4. Segurança e Privacidade

- Senhas com hash (bcrypt/argon2 via provedor de auth) — nunca texto puro.
- Comunicação add-on ↔ backend e web ↔ backend exclusivamente via HTTPS.
- Sugestões e comentários vinculados ao autor autenticado — sem submissão anônima no MVP, para permitir moderação e responsabilização.
- **Sanitização de HTML** gerado pelo editor rich text (US-05/06) antes de persistir ou renderizar para outros usuários — o campo aceita HTML livre (compatível com os campos nativos do Anki), o que é superfície de XSS armazenado se não for filtrado (allowlist de tags/atributos, sem `<script>`/handlers inline).
- Dados pessoais coletados limitados ao necessário para autenticação (e-mail); sem coleta de dados sensíveis de terceiros.
- Rate limiting nos endpoints de sincronização e submissão de sugestões (`django-ratelimit` ou equivalente) para evitar abuso/sobrecarga.
- **Conformidade com a LGPD:** base legal de consentimento explícito e granular para uso de dados em pesquisa e e-mails de marketing (US-01), direito de exclusão de conta com carência de 7 dias e direito de portabilidade via exportação de dados (US-13).

### 4.5. Requisitos Não Funcionais

- **RNF-001 (Design Responsivo):** interface *mobile-first*; todas as telas do MVP devem ser funcionais em viewport de 360px de largura sem scroll horizontal.
- **RNF-002 (Performance de Navegação):** transições de página e renderização de preview de nota devem responder em até 500ms sob carga típica (deck de até 10 mil notas), medido via Web Vitals (LCP) no ambiente de produção.

### 4.6. Arquitetura e Empacotamento do Add-on

O comportamento funcional do add-on (sync, proteção de campos/tags, sugestões) já está definido em US-05/06/08/12. Esta seção cobre como ele é **estruturado e distribuído**, replicando a organização comprovada do add-on real do AnkiHub (analisado a partir do pacote publicado no AnkiWeb, ID 1322529746) para garantir compatibilidade com o backend Django + DRF já decidido.

**Estrutura de módulos** (separação por responsabilidade, não um único arquivo monolítico):
- `main/` — lógica de negócio pura (import/sync, conversão de nota, exclusão, sugestões, mídia), sem dependência de UI; é o que faz a ponte entre o cache local e a coleção do Anki.
- `db/` — cache local em SQLite/peewee (schema já definido nas ACs de US-08/US-12: notas, tipos de nota, mídia de deck).
- `[nome]_client/` — cliente HTTP dedicado, isolado do resto do add-on: única camada que fala com nosso backend (monta requests, autentica, faz retry/backoff). Trocar de backend ou versionar a API deve significar mexer só aqui.
- `gui/` — telas Qt: menu do add-on, diálogo de "Sugerir mudança"/"Sugerir nota nova" (US-05/06) integrado ao editor de nota nativo do Anki, diálogo de configuração de campos/tags protegidos (US-12), diálogo de login.
- Arquivos de configuração na raiz: `manifest.json` (metadados exigidos pelo AnkiWeb: nome, versão, compatibilidade), `config.json` (preferências do usuário expostas via tela de config nativa do Anki, ex.: gatilho de sync automático de US-08), `entry_point.py` (registra os hooks na inicialização).

**Hooks/pontos de integração com o Anki:**
- `profile_did_open` / `profile_will_close` — inicializa e finaliza o add-on junto do perfil do usuário.
- `sync_did_finish` — usado para coordenar timing, não para injetar dados no sync nativo.
- Monkey-patch em `AnkiQt._sync_collection_and_media` — implementa o gatilho "sync encadeado antes do AnkiWeb" (US-08, opção c).
- Botão dedicado no editor de nota — abre o fluxo de sugestão (US-05/06) sem sair do Anki.

**Compatibilidade de versões do Anki/Qt:** o Anki migrou de PyQt5 para PyQt6 entre versões, e isso quebra add-ons que assumem uma binding específica. Manter grupos de dependência separados por faixa de versão suportada (ex.: build atual vs. build para a LTS anterior do Anki Desktop) e testar ambas antes de publicar uma atualização — mesma estratégia do add-on original. Testes automatizados via `pytest-anki` (plugin oficial do próprio ecossistema Anki para simular o ambiente do Anki Desktop em testes).

**Empacotamento e distribuição via AnkiWeb:**
- O add-on roda num ambiente sem acesso a `pip install` em runtime — qualquer dependência que não vem embutida no Anki (o client HTTP, peewee, etc.) precisa ser **vendorizada dentro do pacote `.ankiaddon`** no momento do build, não instalada depois.
- Publicação e atualização acontecem via AnkiWeb (ankiweb.net/shared) — o próprio Anki Desktop verifica e aplica atualizações do add-on automaticamente; não é um mecanismo que construímos.
- Como o Anki não força o usuário a atualizar o add-on imediatamente, o backend deve **tolerar clientes de versões anteriores da API por um período de transição** (aproveitando o versionamento via header `Accept` já decidido em 4.3) em vez de quebrar quem ainda não atualizou.

**Contrato de compatibilidade com o backend:** a URL do backend é configurável no add-on (não hardcoded), permitindo apontar para ambientes de staging/produção — mesmo padrão do AnkiHub original (`ANKIHUB_APP_URL`). O client consome exatamente as convenções REST já fixadas em 4.2/4.3 (rotas com barra final, paginação por cursor, autenticação por token, endpoints de sugestão em lote), então qualquer mudança nesse contrato do lado do backend precisa ser avaliada quanto à quebra de compatibilidade com add-ons já instalados antes de ir para produção.

---

## 5. Riscos e Roadmap

### 5.1. Rollout em Fases

**MVP (Fase 1):**
- Cadastro/login com onboarding e consentimentos LGPD (US-01), catálogo de decks com recomendação básica (US-02), visualização e busca de notas, comentários gerais na nota (US-04), sugestão de mudança/nota nova/exclusão com editor rich text (US-05/06/07), assinatura + sincronização via add-on (US-08), tela pública de Community Suggestions com like/dislike e discussão por sugestão (US-09), decisão de moderação (US-10), múltiplos moderadores por deck (US-11), proteção de campos/tags pessoais (US-12), gestão de conta e privacidade (US-13), denúncia de conteúdo abusivo (US-14).

**v1.1:**
- **Fila assíncrona (Celery + Redis)**, introduzida junto com as notificações abaixo — é o que viabiliza processá-las (e futuras propagações de sync pesadas) em background em vez de bloquear a request; réplica de infraestrutura confirmada no AnkiHub original.
- Notificações (web/e-mail) quando uma sugestão é aceita/rejeitada, quando há novidade em deck assinado, ou quando os metadados do deck (descrição, tags) são atualizados pelo moderador.
- Optional Tag Groups: extensões de tags criadas por qualquer usuário sobre um deck de terceiros (ex.: tags por banca/edital), que outros assinantes escolhem sincronizar por cima do deck base.
- Histórico básico de alterações por nota (quem mudou o quê e quando).
- Melhorias de busca (filtros avançados, busca por tag dentro do deck).

**v2.0:**
- Hierarquia/permissões granulares entre moderadores de um mesmo deck, se a operação com nível único (MVP) se mostrar insuficiente.
- Recursos de IA: busca inteligente de flashcards por vídeo/PDF ("Smart Search") e chatbot de estudo (ver Seção 3).
- Parcerias de conteúdo com cursinhos e editoras jurídicas/fiscais para material licenciado dentro da plataforma (equivalente às parcerias do AnkiHub original com First Aid Forward/McGraw Hill).
- Exploração de monetização (se validada a tração do MVP gratuito).
- App mobile nativo ou PWA instalável, se a demanda mobile justificar além do responsivo.

### 5.2. Riscos Técnicos

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Conflitos de sincronização (merge conflicts) entre edições locais no Anki e mudanças aceitas na web | Alto — pode corromper, duplicar ou apagar notas/anotações pessoais no cliente | Base web é sempre a fonte da verdade para o conteúdo do deck; add-on nunca envia edições locais de volta no MVP (sincronização é unidirecional: web → Anki local, via fluxo de sugestão); campos/tags marcados como protegidos pelo usuário (US-12) são preservados mesmo assim; delta inconsistente demais (ex.: note type mudou de estrutura) força ressincronização completa do deck em vez de aplicar parcialmente (US-08) |
| Divergência de schema entre versões do Anki (mudanças no formato SQLite nativo) | Médio — quebra de compatibilidade em RF-005 | Mapear apenas os campos estáveis da API pública do Anki; testar contra as versões LTS do Anki Desktop |
| Custo de infraestrutura escalar mal com crescimento | Médio — pode gerar surpresa de custo ou downtime | Plano Free do Supabase cobre Auth até 50k MAU (bem acima da meta de baseline do MVP) e DB até 500 MB/1 GB storage; o gargalo real tende a ser tamanho de banco/storage, não Auth. Risco concreto do Free: projeto pausa após 7 dias de inatividade — mitigar com um ping/health-check periódico durante fases de baixo uso. Plano Pro ($25/mês) resolve pausa automática e sobe os limites (100k MAU, 8 GB DB) antes de precisar de um tier maior |
| Qualidade de sugestões (spam ou baixa qualidade sobrecarregando moderadores) | Médio — desmotiva moderadores voluntários | Exigir autenticação, tipo de mudança e justificativa obrigatória para sugerir (já no MVP); o sinal de like/dislike da comunidade (US-09) ajuda a priorizar a fila do moderador; avaliar rate limit por usuário se necessário |
| Conteúdo malicioso via editor rich text (HTML livre nos campos) | Alto — XSS armazenado atingindo outros assinantes | Sanitização de HTML no backend antes de persistir/renderizar (ver Segurança, Seção 4.4) |
| Ausência de app mobile nativo pode limitar uso do add-on (que é desktop-only) | Baixo/Médio — usuários só sincronizam quando abrem o Anki Desktop | Aceito como restrição inerente ao Anki; fora de escopo resolver no MVP |
| Conteúdo ofensivo, difamatório ou spam em comentários/discussões públicas (nicho de concursos frequentemente toca direito e política) | Médio — exposição legal (Marco Civil da Internet exige remoção mediante notificação) e dano à reputação da plataforma | Denúncia de conteúdo (US-14) com revisão pela equipe; termos de uso deixam claro que a responsabilidade pelo conteúdo é do autor; remoção mediante notificação, conforme Marco Civil |
| Fragmentação de versões do add-on em produção (Anki não força atualização imediata) quebrando ao mudar o contrato da API | Médio — usuários com add-on desatualizado passam a ter erro de sincronização | Versionamento de API via header `Accept` (4.3/4.6); backend mantém compatibilidade com a versão anterior por um período de transição antes de descontinuar um contrato antigo |

### 5.3. Decisões em Aberto (`TBD`)

- Metas numéricas definitivas dos KPIs da Seção 1 (atualmente sugestões de baseline).
- Prazo/deadline de lançamento — não definido pelo usuário.
- Revisão da hospedagem do backend após o primeiro ano (quando os créditos do Heroku expiram) — migrar para Railway/Render/Fly.io ou renovar em Heroku pago, a decidir com base no custo real observado.

> Resolvidas nesta revisão: framework de backend (Django + DRF, ver 4.3), estratégia de mídia (Supabase Storage/S3-compatible, ver 4.3) e hospedagem do backend para o ano 1 (Heroku + Supabase região EUA, ver 4.3).
