# Auditoria técnica mobile-first — 360 px

Data: 2026-07-13

## Resultado verificável

As 16 rotas implementadas foram abertas em Chromium headless com viewport de
360 × 800 px. Em todas, `document.documentElement.scrollWidth` permaneceu igual
a `clientWidth` (360 px), sem elemento ultrapassando as bordas do viewport.

Rotas verificadas: `/`, `/login`, `/register`, `/password-reset`, `/account`,
`/account/privacy`, `/decks`, detalhe de deck, moderadores, notas, sugestão de
edição, sugestão de exclusão, proteção, sugestão em massa, sugestão de nota nova
e Community Suggestions.

## Audit Health Score

| # | Dimensão | Nota | Achado principal |
|---|---|---:|---|
| 1 | Acessibilidade | 2/4 | Controles globais e legados têm alvos de 28–40 px. |
| 2 | Performance | 4/4 | Nenhum padrão de renderização ou animação caro foi encontrado. |
| 3 | Design responsivo | 3/4 | 16/16 rotas passam a 360 px; alvos de toque ainda são pequenos. |
| 4 | Temas | 2/4 | Telas novas usam tokens; home e formulários legados mantêm cores locais. |
| 5 | Antipadrões | 2/4 | A home ainda é o template genérico em inglês do Next.js. |
| **Total** | | **13/20** | **Aceitável — correções significativas pendentes.** |

## Veredito de antipadrões

Falha parcial. As telas funcionais têm hierarquia contida e não exibem os
principais sinais de “AI slop”. Porém, a home padrão do Next.js torna o produto
genérico e inconsistente com o restante da navegação.

## Achados priorizados

### [P1] Alvos de toque menores que 44 px

- **Local:** `frontend/src/components/ui/button.tsx:23` e controles legados.
- **Categoria:** Acessibilidade / Responsivo.
- **Impacto:** pessoas com baixa precisão motora podem errar o toque; o botão de
  tema mede 32 × 32 px e ações do cabeçalho medem 28 px de altura.
- **Padrão:** WCAG 2.5.8 (Target Size) e recomendação móvel de 44 × 44 px.
- **Recomendação:** elevar o tamanho interativo móvel, preservando densidade a
  partir de breakpoints maiores.
- **Comando sugerido:** `$impeccable adapt`.

### [P1] Home não representa o produto

- **Local:** `frontend/src/app/page.tsx:8`.
- **Categoria:** Antipadrão / Localização.
- **Impacto:** a primeira visita apresenta logo e instruções do Next.js em
  inglês, sem caminho claro para catálogo ou cadastro.
- **Recomendação:** substituir por uma entrada curta do AnkiHub Brasil em pt-BR.
- **Comando sugerido:** `$impeccable shape`.

### [P2] Dois sistemas visuais coexistem

- **Local:** `frontend/src/app/globals.css:34` e
  `frontend/src/app/page.module.css:1`.
- **Categoria:** Tema / Consistência.
- **Impacto:** formulários antigos e home não acompanham integralmente tokens e
  dark mode do design system.
- **Recomendação:** concluir o retrofit Tailwind/shadcn da T109 e remover CSS
  legado sem consumidores.
- **Comando sugerido:** `$impeccable colorize`.

### [P2] Overflow global é ocultado

- **Local:** `frontend/src/app/globals.css:11`.
- **Categoria:** Responsivo.
- **Impacto:** `overflow-x: hidden` pode recortar conteúdo futuro e esconder uma
  regressão em vez de permitir diagnóstico.
- **Recomendação:** remover a regra depois do retrofit e manter um teste de
  viewport que falhe quando `scrollWidth > clientWidth`.
- **Comando sugerido:** `$impeccable harden`.

## Padrões sistêmicos

- Os componentes funcionais novos são mobile-first (`flex-col`/`grid-cols-1`
  antes dos breakpoints) e usam limites fluidos.
- Os tamanhos compactos do componente `Button` propagam alvos menores que 44 px
  a várias telas.
- O legado (`.form-page`, `.deck-list` e `page.module.css`) concentra as cores
  fora do sistema de tokens.

## Pontos positivos

- Nenhuma rolagem horizontal foi observada nas 16 rotas a 360 px.
- Formulários funcionais têm largura fluida e campos não excedem o viewport.
- Novas telas usam landmarks, trilha de navegação, estados de erro e regiões
  anunciáveis com consistência.
- Dark mode está conectado à classe `.dark` e as novas telas usam tokens.

## Ações recomendadas

1. **[P1] `$impeccable adapt`:** ampliar alvos móveis na T108/T109.
2. **[P1] `$impeccable shape`:** substituir a home padrão e localizar seu texto.
3. **[P2] `$impeccable colorize`:** eliminar estilos legados na T109.
4. **[P2] `$impeccable harden`:** automatizar a verificação de overflow.
5. **[P2] `$impeccable polish`:** repetir a auditoria após as correções.

