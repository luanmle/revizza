# Data Model Delta: Suporte a Decks com Múltiplos Tipos de Nota

Este documento descreve apenas as mudanças em relação a
`specs/001-ankihub-brasil-mvp/data-model.md`. Entidades não citadas aqui permanecem inalteradas.

## Deck

| Campo | Antes | Depois |
|---|---|---|
| `note_type` | FK obrigatória → NoteType ("um deck usa um tipo de nota") | **Removido.** O conjunto de tipos de nota do deck passa a ser derivado via `NoteType.objects.filter(notes__deck=deck).distinct()` (ver `research.md` → Decisão 1). Nenhuma coluna nova substitui a FK removida — a relação já existe, de forma independente, em `Note.note_type`. |

**Migração**: schema-only (remove a coluna/FK `note_type_id` de `Deck`); nenhuma migração de **dados**
é necessária — cada `Note` já carrega seu próprio `note_type_id` desde o MVP, então nenhuma informação
é perdida ao remover a FK do `Deck`. Decks publicados antes desta feature continuam com exatamente uma
linha em `NoteType` associada via suas notas (comportamento observável idêntico ao anterior — SC-003).

## NoteType

Sem mudanças de schema. Continua representando um tipo de nota individual (campos, templates, CSS,
`structure_changed_at`).

## Note

Sem mudanças de schema. `note_type` já era uma FK própria por nota (`specs/001-ankihub-brasil-mvp/
data-model.md`, seção Note) — esta feature passa a tratá-la como única fonte da verdade para
validação/sync, em vez de um atalho via `deck.note_type`.

## Suggestion

| Campo | Antes | Depois |
|---|---|---|
| `note_type` | Não existia | **Novo**: FK nullable → NoteType, `on_delete=PROTECT`. Preenchida apenas quando `type=new_note`; deve ser um dos tipos de nota já presentes no deck da sugestão (validado na criação — ver `research.md` → Decisão 4). Nula para `type=change`/`deletion`, onde o tipo de nota é sempre o da(s) nota(s)-alvo já existente(s). |

**Migração**: adiciona coluna nullable — não requer backfill (sugestões `new_note` existentes, se
houver, pertencem a decks que hoje só têm um tipo de nota; podem ficar com `note_type=null` sem quebrar
nada, já que a leitura desse campo só é exigida em sugestões `new_note` **novas**, criadas depois desta
feature). Nenhum FR pede reprocessar sugestões antigas.

## Regra de invariante nova

- Uma sugestão do tipo `change` (individual ou `bulk-change`) só pode ter notas-alvo que pertençam
  todas ao **mesmo** `NoteType` — validado na aplicação (não no schema), pelo motivo descrito em
  `research.md` → Decisão 4. Isso não existia como restrição explícita antes porque, com um único tipo
  de nota por deck, era impossível violá-la.
