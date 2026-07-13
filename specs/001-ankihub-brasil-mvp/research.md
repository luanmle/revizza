# Phase 0 Research: AnkiHub Brasil — MVP

Todas as decisões abaixo foram tomadas diretamente (sem marcadores `NEEDS CLARIFICATION`
pendentes), conforme pedido do usuário para tomar as melhores escolhas dentro dos limites já
fixados pelo PRD e pela Constituição (Django+DRF, Next.js, Supabase, Heroku, add-on Python).

## 1. Editor rich text (WYSIWYG) — FR-014

- **Decision**: Tiptap (construído sobre ProseMirror), integrado ao Next.js/React.
- **Rationale**: Gera HTML limpo e previsível por padrão (mais fácil de casar com a allowlist de
  sanitização do backend do que editores baseados em `contenteditable` livre); tem extensões prontas
  para exatamente os controles pedidos em FR-014 (negrito, itálico, sublinhado, tachado, listas,
  alinhamento, links, tamanho de fonte) e para alternar para edição do HTML bruto. É a escolha mais
  comum do ecossistema React para este caso de uso, reduzindo risco de manutenção.
- **Alternatives considered**: Quill (API mais rígida para customizar toolbar, saída de HTML menos
  previsível para casar com a allowlist do backend); Slate (exige montar toolbar e serialização HTML
  do zero — mais código do que o problema justifica no MVP).

## 2. Sanitização de HTML no backend — FR-015

- **Decision**: `nh3` (bindings Python para o `ammonia`, escrito em Rust) com allowlist de
  tags/atributos compatível com o que o Anki nativamente aceita em campos (negrito, itálico,
  sublinhado, tachado, listas, links, `<span style="...">` para tamanho de fonte, `<img>` para mídia
  já referenciada).
- **Rationale**: Mais rápido e com superfície de API mais simples que `bleach` (que depende de
  `html5lib`, mais lento e com mais CVEs históricos de bypass de allowlist); mantido ativamente.
  Sanitizar no backend (não só no frontend) é obrigatório porque a mesma nota é lida por outros
  assinantes e, futuramente, por qualquer cliente da API — nunca confiar em sanitização client-side
  como única defesa.
- **Alternatives considered**: `bleach` (mais lento, ecossistema de manutenção mais fraco);
  sanitizar somente no frontend (rejeitado — não protege contra clientes de API diretos).

## 3. Paginação e convenções de API — FR-006, FR-021, PRD §4.2

- **Decision**: DRF `CursorPagination` (campo `next`) como paginador default do projeto; todas as
  rotas com barra final (`APPEND_SLASH` padrão do Django, sem alteração); endpoint de sugestão em
  lote dedicado (`POST /suggestions/bulk-change/`) que aceita uma lista de notas-alvo.
- **Rationale**: Replica literalmente as convenções já observadas na API pública do AnkiHub original
  (Princípio I da Constituição — Parity Over Reinvention), e `CursorPagination` é nativo do DRF, sem
  código extra.
- **Alternatives considered**: `PageNumberPagination` (mais simples, mas diverge da convenção
  observada e degrada em listagens que mudam com frequência, como Community Suggestions).

## 4. Cache local de sincronização no add-on — US-08, FR-034

- **Decision**: `peewee` + SQLite, em um arquivo separado do `collection.anki2` nativo, guardado na
  pasta de dados do add-on (`user_files/`).
- **Rationale**: É a própria sugestão do PRD (§4.1); `peewee` é uma ORM leve o suficiente para não
  competir com a complexidade do add-on em si, e manter a tabela de estado fora do banco nativo do
  Anki evita qualquer risco de corromper a coleção do usuário com um schema não reconhecido pelo
  próprio Anki.
- **Alternatives considered**: Guardar o estado de sync em uma tag/campo dentro do próprio Anki
  (rejeitado — poluiria a coleção do usuário e conflitaria com a convenção de tags de proteção já
  definida em FR-039/FR-040).

## 5. Interceptação do sync nativo do Anki — US-08 (gatilho encadeado)

- **Decision**: Ciclo de vida do add-on via `gui_hooks.profile_did_open`/`profile_will_close`
  (inicializa/finaliza junto do perfil do usuário); `gui_hooks.sync_did_finish` usado apenas para
  coordenar timing (nunca para injetar dados no sync nativo); o gatilho "encadeado antes do AnkiWeb"
  (US-08, opção c) é implementado via monkey-patch em `AnkiQt._sync_collection_and_media`, que roda
  a sincronização própria e só então deixa o método original prosseguir — réplica direta da técnica
  do add-on real do AnkiHub (PRD §4.6, add-on ID 1322529746 no AnkiWeb).
- **Rationale**: É a mesma abordagem já comprovada em produção pelo add-on original, o que reduz o
  risco de regressão a cada atualização do Anki Desktop (Princípio I — Parity Over Reinvention);
  usar hooks documentados sempre que possível (`profile_did_open`, `sync_did_finish`) e reservar o
  monkey-patch apenas para o único ponto (encadear antes do sync nativo) que o Anki não expõe via
  hook oficial. Suporta diretamente FR-038 (apenas a LTS mais recente) como alvo de teste.
- **Alternatives considered**: Depender só de hooks documentados sem nenhum monkey-patch (rejeitado
  — o Anki não expõe um hook "antes do sync nativo, bloqueante", então o gatilho encadeado exigiria
  cooperação do usuário para acionar duas ações manuais em vez de uma).

## 6. E-mail transacional — US-01 (verificação), US-11 (convite), US-13, US-14 (notificação)

- **Decision**: Verificação de cadastro e recuperação de senha usam o mecanismo nativo do Supabase
  Auth (já incluso, zero infraestrutura extra). Para os e-mails específicos do domínio do produto
  (convite de co-moderador, notificação de remoção de conteúdo) usar o backend de e-mail padrão do
  Django (`django.core.mail`) configurado via SMTP por variáveis de ambiente, enviado de forma
  síncrona dentro da própria request.
- **Rationale**: Consistente com o Princípio V (YAGNI) — o volume do MVP (baseline de 500 usuários)
  não justifica fila assíncrona (Celery/Redis é explicitamente v1.1 no PRD §5.1); enviar de forma
  síncrona é a opção mais simples que ainda funciona. Não amarrar a um provedor específico no código
  mantém a escolha de provedor (ex.: Postmark, Resend, SMTP do próprio Heroku) como uma decisão de
  configuração de deploy, não de arquitetura.
- **Alternatives considered**: Fila assíncrona dedicada para e-mail (rejeitado agora — antecipa
  infraestrutura do roadmap v1.1 sem necessidade comprovada no MVP).

## 7. Versão do Anki Desktop suportada — FR-038

- **Decision**: O add-on declara suporte apenas à versão LTS do Anki Desktop vigente no momento do
  release (identificada via `anki.buildinfo.version` em tempo de execução), sem fixar um número de
  versão específico neste documento — o número exato muda ao longo do tempo e não deve ser
  hardcoded na spec/plano.
- **Rationale**: Fixar aqui uma versão concreta (ex. "24.11") ficaria obsoleto assim que o Anki
  lançar a próxima LTS; a política ("apenas a LTS mais recente") é o que importa para o design, e
  fica testável via CI apontando para a LTS vigente no momento do build.
- **Alternatives considered**: Hardcodar uma versão mínima fixa no manifesto do add-on (rejeitado —
  vira dívida de manutenção a cada novo lançamento LTS do Anki).

## 8. Testes do add-on sem depender do Anki Desktop instalado

- **Decision**: `pytest-anki` — plugin oficial do ecossistema Anki que simula o ambiente do Anki
  Desktop (incluindo `aqt`/`gui_hooks` e uma `Collection` real em SQLite temporário) dentro de testes
  pytest, sem precisar da aplicação desktop completa nem de display gráfico (PRD §4.6).
- **Rationale**: É a mesma ferramenta usada pelo add-on original do AnkiHub para este fim (Princípio
  I); shipar com o mecanismo de teste já validado pelo próprio ecossistema evita reinventar fixtures
  de coleção do zero e cobre também os hooks/monkey-patches da decisão §5 acima, não só o schema.
- **Alternatives considered**: Montar fixtures de `Collection` manualmente com `anki`/`aqt` crus
  (mais código de infraestrutura de teste do que necessário, já resolvido pelo `pytest-anki`);
  mockar inteiramente a API do Anki (rejeitado — perde cobertura real do comportamento de
  delta/proteção contra o schema nativo, que é justamente o que está em risco segundo o PRD §5.2).

## 9. Compatibilidade PyQt5 → PyQt6 do Anki Desktop

- **Decision**: Manter grupos de dependência separados por faixa de versão suportada do Anki (build
  para a LTS vigente vs. build para a LTS anterior, se ambas estiverem em uso relevante) e rodar a
  suíte `pytest-anki` contra as duas antes de publicar uma atualização do add-on.
- **Rationale**: O Anki já migrou de PyQt5 para PyQt6 entre versões, quebrando add-ons que assumem
  um binding específico; é a mesma estratégia usada pelo add-on original (PRD §4.6). Testar as duas
  faixas é mais barato do que descobrir a quebra via relatos de usuário em produção.
- **Alternatives considered**: Suportar apenas a LTS vigente sem testar a anterior (aceitável dado
  FR-038, mas arriscado durante a janela de transição logo após uma nova LTS ser lançada — manter o
  teste contra a build anterior enquanto uma parcela relevante de usuários ainda não migrou).

## 10. Empacotamento e vendoring de dependências do add-on

- **Decision**: Toda dependência não embutida no Anki (cliente HTTP, `peewee`) é vendorizada dentro
  do pacote `.ankiaddon` no momento do build — o ambiente de execução do add-on não tem `pip install`
  em runtime (PRD §4.6).
- **Rationale**: É uma restrição de plataforma, não uma escolha de design — o Anki carrega add-ons
  como código Python puro dentro do próprio processo, sem gerenciador de pacotes disponível.
- **Alternatives considered**: Nenhuma — restrição inerente à plataforma de distribuição de add-ons
  do Anki (AnkiWeb).

## 11. Versionamento da API e compatibilidade retroativa do add-on

- **Decision**: Versionamento via header `Accept` (já confirmado no PRD §4.3/§4.6 como convenção
  observada no AnkiHub original); o backend mantém suporte a pelo menos uma versão anterior do
  contrato por um período de transição sempre que uma mudança breaking for necessária.
- **Rationale**: O Anki não força atualização imediata de add-ons — eles são atualizados quando o
  usuário abre o Anki e aceita a atualização via AnkiWeb, então existirá sempre uma janela com
  múltiplas versões do add-on em produção simultaneamente (risco documentado no PRD §5.2:
  "Fragmentação de versões do add-on"). Quebrar contrato sem transição derruba sync de quem não
  atualizou ainda.
- **Alternatives considered**: Forçar todos os clientes a atualizar imediatamente (impossível — Anki
  não dá esse controle ao autor do add-on); versionar via path (`/v1/`, `/v2/`) em vez de header
  (rejeitado — diverge da convenção já observada no AnkiHub original, Princípio I).

## 12. URL do backend configurável no add-on

- **Decision**: URL do backend é um valor de configuração do add-on (`config.json`, tela de
  configuração nativa do Anki), nunca hardcoded — mesmo padrão do AnkiHub original (`ANKIHUB_APP_URL`).
- **Rationale**: Permite apontar o mesmo add-on para staging/produção sem rebuild, e é a mesma
  convenção já usada pelo produto de referência (Princípio I).
- **Alternatives considered**: Hardcoded por ambiente de build (rejeitado — exige builds separados
  só para trocar de ambiente, sem necessidade).

## 13. Isolamento visual do preview de nota — FR-011 (clarificado em 2026-07-13)

- **Decision**: O preview de nota é renderizado em um `<iframe sandbox srcDoc="...">` contendo
  apenas o `NoteType.css` + o HTML sanitizado da nota (`field_values` já processado por `nh3`),
  sem nenhuma folha de estilo do design system do frontend injetada no documento do iframe.
  Atributo `sandbox` sem `allow-scripts` (o HTML já é sanitizado no backend, mas o iframe é a
  segunda camada de defesa — Princípio IV).
- **Rationale**: Um `<iframe>` com documento próprio garante isolamento total de CSS (nenhuma
  regra do Tailwind/shadcn pode vazar para dentro, nem o CSS da nota pode vazar para fora),
  satisfazendo a exigência de fidelidade ao template/CSS original do Anki (FR-011) sem gambiarras
  de especificidade CSS. É mais simples de garantir corretamente do que Shadow DOM, que isola
  estilo mas ainda compartilha o mesmo documento/contexto de execução JS da página.
- **Alternatives considered**: Shadow DOM (`attachShadow`) — isola CSS mas exige disciplina manual
  para não vazar estilo global via `:host`/herança de propriedades, e não adiciona a mesma barreira
  de execução que o `sandbox` de um iframe; CSS scoping via prefixo de classe/CSS Modules
  (rejeitado — falso senso de isolamento, uma regra global `*` do design system ainda alcançaria
  o preview).

## 14. Stack de estilo do frontend e pipeline de design (Constituição v1.1.0, Princípio VII)

- **Decision**: Tailwind CSS 4 + shadcn/ui (preset `base-nova`, cor base neutral, ícones lucide)
  como base de estilo do frontend, já instalados e com build verificado. Componentes de UI
  adicionados via shadcn MCP (registro oficial) em vez de reimplementados à mão. Um
  `design-system/MASTER.md` (gerado pela skill `ui-ux-pro-max:design-system`) é a referência
  persistente de paleta/tipografia/tokens/componentes-base para toda tela nova; a skill
  `impeccable` audita cada tela (contraste AA, hierarquia visual, remoção de estilo genérico de
  IA) antes de considerá-la pronta.
- **Rationale**: Evita que cada tela nova invente seu próprio visual (risco já observado nas telas
  de US1/US2, construídas antes desta decisão, que precisam de retrofit). shadcn sobre Radix
  cobre com acessibilidade de teclado nativa boa parte do FR-055 (tabs, dialog, dropdown) sem
  código adicional — reduz o custo de atender FR-055 nas telas mais densas (US4/US5).
- **Alternatives considered**: CSS Modules manuais sem biblioteca de componentes (era o estado do
  frontend antes desta decisão — descartado por exigir reconstruir do zero primitives
  acessíveis como tabs/dialog que o FR-055 exige); outra biblioteca de componentes sem MCP
  integrado ao editor (perderia o ganho de produtividade de adicionar componentes por pedido
  em linguagem natural).
