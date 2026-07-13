# Design System — AnkiHub Brasil (MASTER)

Fundação visual de todas as telas do MVP. Gerado via `ui-ux-pro-max:design-system` (T107).
Toda tela nova ou retrabalhada parte daqui (Constituição, Princípio VII).

**Produto**: ferramenta autenticada de estudo e moderação para concurseiros — sessões longas,
conteúdo denso (flashcards, diffs, filas de sugestão). **Modo Product, não Brand**: superfícies
neutras e calmas, uma única cor de marca confiante, vocabulário de status forte.

---

## 1. Princípios

1. **Verde aprovação**: a cor da marca é verde-esmeralda — "aprovação" é o objetivo do usuário
   (passar no concurso) e a ação central da plataforma (sugestão aceita).
2. **Status é vocabulário**: `pending`/`accepted`/`rejected` aparecem em todo o domínio;
   âmbar/verde/vermelho são tokens semânticos, nunca cores ad hoc.
3. **Conteúdo primeiro**: campos de nota e diffs são o centro da tela; chrome (header, filtros)
   fica em neutros.
4. **Mobile-first 360px** (FR-053), **animações ≤ 500ms** (FR-054), **contraste AA** (FR-055),
   **copy 100% pt-BR** (FR-056).
5. **Ponytail**: use os componentes shadcn/ui do registry (`components.json`, estilo `base-nova`);
   não recrie o que o registry fornece.

## 2. Paleta

### Primitivos (Tailwind 4, oklch)

| Primitivo     | Valor                             | Uso                                              |
| ------------- | --------------------------------- | ------------------------------------------------ |
| `neutral-*`   | escala padrão Tailwind            | superfícies, texto, bordas (já em `globals.css`) |
| `emerald-400` | `oklch(0.765 0.177 163.223)`      | primary dark-mode, accepted dark-mode            |
| `emerald-600` | `oklch(0.596 0.145 163.225)`      | success/accepted light-mode                      |
| `emerald-700` | `oklch(0.508 0.118 165.612)`      | **primary light-mode** (4.5:1+ sobre branco)     |
| `emerald-950` | `oklch(0.262 0.051 172.552)`      | foreground sobre primary dark-mode               |
| `amber-300`   | `oklch(0.879 0.169 91.605)`       | warning/pending dark-mode                        |
| `amber-700`   | `oklch(0.555 0.163 48.998)`       | warning/pending light-mode                       |
| vermelho      | tokens `--destructive` existentes | rejected, erros, exclusão                        |

### Semânticos (definidos em `src/app/globals.css`)

| Token                                         | Light                     | Dark        | Propósito                            |
| --------------------------------------------- | ------------------------- | ----------- | ------------------------------------ |
| `--primary`                                   | emerald-700               | emerald-400 | ações principais, links ativos, foco |
| `--primary-foreground`                        | branco                    | emerald-950 | texto sobre primary                  |
| `--success`                                   | emerald-600               | emerald-400 | sugestão aceita, confirmações        |
| `--warning`                                   | amber-700                 | amber-300   | sugestão pendente, avisos            |
| `--destructive`                               | (existente)               | (existente) | sugestão rejeitada, erros, exclusão  |
| `--ring`                                      | emerald-600               | emerald-400 | anel de foco visível (teclado)       |
| demais (`--background`, `--card`, `--muted`…) | neutros shadcn existentes | idem        | superfícies                          |

Uso em Tailwind: `bg-primary`, `text-success`, `text-warning`, `bg-success/15` (soft badge), etc.

### Componentes (exemplos de mapeamento)

```css
/* badge de status = semântico, nunca primitivo */
pendente:  bg-warning/15  text-warning
aceita:    bg-success/15  text-success
rejeitada: bg-destructive/15 text-destructive
```

Diff (FR-016): remoção `bg-destructive/15`, adição `bg-success/15`, sobre `--card`.

## 3. Tipografia

| Papel                       | Fonte                                  | Classe               |
| --------------------------- | -------------------------------------- | -------------------- |
| Corpo e headings            | Geist Sans (`next/font`, já carregada) | `font-sans` (padrão) |
| HTML bruto / código / GUIDs | Geist Mono                             | `font-mono`          |

Escala (Tailwind padrão — não inventar tamanhos):

| Uso                                | Classe                                            |
| ---------------------------------- | ------------------------------------------------- |
| Título de página (h1)              | `text-2xl font-semibold tracking-tight`           |
| Título de seção/card (h2)          | `text-lg font-semibold`                           |
| Corpo                              | `text-base` (mobile) / `text-sm` (tabelas densas) |
| Metadados (autor, data, contagens) | `text-sm text-muted-foreground`                   |
| Labels de formulário               | `text-sm font-medium`                             |

## 4. Espaçamento, raio, sombra, movimento

- **Espaçamento**: escala Tailwind; página `p-4` (mobile) / `p-6` (≥768px); gap entre cards `gap-4`.
- **Container**: conteúdo `max-w-3xl mx-auto`; telas de formulário `max-w-md mx-auto`.
- **Raio**: `--radius: 0.625rem` (existente) — cards/inputs `rounded-lg`, badges `rounded-full`.
- **Sombra**: `shadow-xs` em cards; nada mais forte (ferramenta, não marketing).
- **Movimento**: transições `duration-150`–`duration-300`, nunca > 500ms (FR-054);
  respeite `prefers-reduced-motion` (tw-animate-css já respeita).

## 5. Tema claro/escuro

- **Estratégia**: classe `.dark` no `<html>` (shadcn class-based). Padrão segue
  `prefers-color-scheme`; alternância manual via `ThemeToggle` no header, persistida em
  `localStorage.theme`. Script inline em `layout.tsx` aplica a classe antes do primeiro paint
  (sem flash). Isso torna os tokens `.dark` de `globals.css` alcançáveis (resolvido em T107).
- `color-scheme` acompanha a classe (`:root { color-scheme: light }`, `.dark { color-scheme: dark }`).

## 6. Componentes base

Adicione via shadcn registry (estilo `base-nova`, ícones lucide). Conjunto do MVP:
`button`, `input`, `textarea`, `select`, `label`, `card`, `badge`, `tabs`, `dialog`,
`skeleton`, `alert`, `checkbox`, `separator`, `dropdown-menu`.

### Button (primário)

| Propriedade | Default              | Hover        | Active       | Disabled           | Focus                            |
| ----------- | -------------------- | ------------ | ------------ | ------------------ | -------------------------------- |
| Background  | `primary`            | `primary/90` | `primary/80` | `muted`            | `primary`                        |
| Texto       | `primary-foreground` | idem         | idem         | `muted-foreground` | idem                             |
| Anel        | —                    | —            | —            | —                  | `ring-2 ring-ring ring-offset-2` |

Variantes: `default` (ações principais: enviar sugestão, assinar), `outline` (secundárias:
filtrar, cancelar), `ghost` (ícones do header), `destructive` (rejeitar, excluir).

### Badge de status de sugestão

| Status     | Classe                               | Rótulo pt-BR |
| ---------- | ------------------------------------ | ------------ |
| `pending`  | `bg-warning/15 text-warning`         | Pendente     |
| `accepted` | `bg-success/15 text-success`         | Aceita       |
| `rejected` | `bg-destructive/15 text-destructive` | Rejeitada    |

Categorias de mudança (FR-013) usam `variant="secondary"` (neutro): Conteúdo atualizado,
Ortografia/Gramática, Erro de conteúdo, Nova tag, Tag atualizada, Outro.

### Formulários

- `Label` sempre visível acima do campo (nunca placeholder como label — acessibilidade).
- Erro por campo: `text-sm text-destructive` logo abaixo do campo, com `role="alert"`.
- Justificativa obrigatória: `Textarea` com contador implícito só se o backend limitar.

### RichTextEditor (Tiptap 3) — spec para T051

- Toolbar compacta: negrito, itálico, sublinhado, riscado, listas, link — somente o que o
  allowlist do backend aceita (`nh3`); nada de headings/tabelas. Sub/sobrescrito ficam
  acessíveis pelo modo HTML (extensões Tiptap extras só se houver demanda — YAGNI).
- Toggle "HTML" (ghost button à direita da toolbar) alterna para `<textarea>` `font-mono`
  com o HTML bruto (FR-014).
- Área editável: `min-h-24 rounded-lg border bg-background p-3 text-base`, foco com `ring`.

### DiffViewer — spec para T052 (FR-016)

- Um bloco por campo alterado, empilhado; dentro do bloco, duas colunas
  ("Atual" | "Sugerido") em `grid-cols-1 md:grid-cols-2` (empilha a 360px).
- Cabeçalho de coluna: `text-sm font-medium text-muted-foreground`.
- Coluna Atual: `bg-destructive/10`; coluna Sugerido: `bg-success/10`; ambas `rounded-lg p-3`.
- HTML renderizado (já sanitizado pelo backend — nunca renderizar HTML não sanitizado).

## 7. Estados de tela

| Estado               | Padrão                                                                                                                                                                                                                     |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Carregando**       | `Skeleton` com a silhueta do conteúdo real (linhas de card, campos). Nunca spinner de página inteira. Botões em submissão: `disabled` + rótulo "Enviando…".                                                                |
| **Vazio**            | Bloco centralizado: ícone lucide `text-muted-foreground`, título curto (`text-lg font-medium`), frase de ação e botão primário quando houver ação. Ex.: "Nenhuma sugestão ainda — Seja o primeiro a sugerir uma melhoria." |
| **Erro**             | `Alert` `variant="destructive"` com mensagem legível do corpo `{"detail": …}` da API e botão "Tentar novamente" quando a query for refazível. 401 → link para `/login`.                                                    |
| **429 (rate limit)** | Aviso `text-warning` com o tempo do `Retry-After`: "Aguarde Xs antes de enviar novamente."                                                                                                                                 |

## 8. Navegação global

### SiteHeader (todas as telas)

- `header` sticky (`sticky top-0 z-40 border-b bg-background/95 backdrop-blur`), altura `h-14`,
  conteúdo `max-w-5xl mx-auto px-4 flex items-center justify-between`.
- **Esquerda**: logotipo textual "AnkiHub **Brasil**" (`font-semibold`, "Brasil" em `text-primary`)
  → link para `/decks`.
- **Direita (autenticado)**: link "Catálogo" (`/decks`), `ThemeToggle`, menu do usuário
  (dropdown: "Minha conta" → `/account`, "Sair").
- **Direita (anônimo)**: `ThemeToggle`, "Entrar" (ghost) → `/login`, "Criar conta" (default)
  → `/register`.
- Em 360px: esconder o link "Catálogo" (o logo já leva ao catálogo); manter toggle + menu.

### Fluxo catálogo → deck → notas → sugestões

```
/decks                         Catálogo (busca por tag, recomendados no topo)
  └─ /decks/[id]               Detalhe do deck (assinar, abas: Notas | Sugestões)
       ├─ /decks/[id]/notes/[noteId]/suggest    Sugerir mudança (editor + diff)
       ├─ /decks/[id]/suggest-bulk              Sugestão em lote (seleção de notas)
       └─ /decks/[id]/suggestions               Sugestões da comunidade (3 abas)
```

- **Breadcrumb** em toda página abaixo do catálogo: `text-sm text-muted-foreground`,
  separador `/`, último item `text-foreground`. Ex.: `Catálogo / Direito Constitucional / Sugerir mudança`.
- Voltar sempre possível pelo breadcrumb — nunca beco sem saída.

## 9. Acessibilidade (FR-055, SC-009)

- Contraste AA: todos os pares acima já validados (primary emerald-700 sobre branco ≥ 4.5:1;
  emerald-400 sobre fundo escuro ≥ 7:1). Nunca âmbar-500/600 como texto sobre branco.
- Foco visível por teclado em todo interativo (`focus-visible:ring-2`).
- Todo `img` de mídia de nota com `alt`; ícones decorativos `aria-hidden`.
- Alvos de toque ≥ 40px de altura em mobile.
- Formulários com `label` associado (`htmlFor`) e erros anunciados (`role="alert"`).

## 10. Débito conhecido

- Nenhum débito visual conhecido nas telas do MVP.
