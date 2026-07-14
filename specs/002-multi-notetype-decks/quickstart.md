# Quickstart: Validando decks com múltiplos tipos de nota

Assume o ambiente já rodando conforme `specs/001-ankihub-brasil-mvp/quickstart.md` (backend, frontend,
add-on carregado em modo dev). Este guia só cobre o cenário novo desta feature — publicar e sincronizar
um deck com mais de um tipo de nota.

## Cenário 1 — Publicar deck misto (US1, SC-001)

1. No Anki local, crie um deck de teste com notas de dois tipos diferentes, ex.:
   - Algumas notas do tipo nativo "Basic".
   - Algumas notas de um tipo de nota customizado, ex. "Cloze Jurídico" (pode ser um clone do tipo
     nativo "Cloze" renomeado).
2. Publique o deck via add-on (menu Revizza → "Criar deck Revizza").
3. **Esperado**: publicação concluída com sucesso (sem o erro "A importação inicial aceita um único
   tipo de nota por deck."); `tooltip` de confirmação mostra a contagem total de notas.
4. Consulte `GET /api/v1/decks/{id}/` — `note_types` deve listar os dois tipos de nota, cada um com o
   `note_count` correto (ver `contracts/catalog.md`).

## Cenário 2 — Sincronizar e revisar (US2, SC-002)

1. Em um perfil Anki limpo, assine o deck publicado no Cenário 1 e sincronize.
2. **Esperado**: os dois tipos de nota são recriados localmente (`Ferramentas → Gerenciar Tipos de
   Nota` no Anki mostra ambos); cada nota renderiza com o template/CSS do seu próprio tipo (abra o
   Navegador do Anki e confira visualmente uma nota de cada tipo).
3. Abra o preview de uma nota de cada tipo na web (`GET /api/v1/notes/{id}/`) e confirme que o preview
   usa o template/CSS correto para aquele tipo específico.

## Cenário 3 — Sugestão de nota nova em deck multi-tipo (Decisão 4 do research.md)

1. Como assinante, abra "Propor nota nova" no deck multi-tipo.
2. **Esperado**: a UI exige escolher qual dos tipos de nota existentes do deck a nova nota vai usar
   (`note_type_id` no payload de `POST /decks/{id}/suggestions/new-note/`); os campos exibidos mudam
   conforme o tipo escolhido.

## Cenário 4 — Regressão em deck de tipo único (SC-003)

1. Repita o Cenário 1 com um deck de um único tipo de nota (fluxo já existente antes desta feature).
2. **Esperado**: nenhuma mudança observável — publica, sincroniza e recebe sugestões exatamente como
   antes; `note_types` no detalhe do deck retorna uma lista com um único item.

## Testes automatizados a rodar

```bash
cd backend && pytest apps/sync apps/protection apps/suggestions apps/catalog -q
cd addon && pytest tests/unit/test_publish.py -q
cd frontend && npx playwright test  # se a US3 já tiver UI implementada
```
