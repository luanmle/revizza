# Phase 0 Research: Suporte a Decks com Múltiplos Tipos de Nota

Nenhum `NEEDS CLARIFICATION` ficou pendente do spec (ver `spec.md` → Assumptions). As decisões abaixo
resolvem as questões arquiteturais reais levantadas pelo pedido do usuário ("proponha a melhor
abordagem arquitetural"), a partir da leitura do código atual (`backend/apps/{catalog,notes,sync,
protection,suggestions}`, `addon/ankihub_br/main/{publish,sync}.py`).

## Decisão 1 — Relação Deck↔NoteType

**Decision**: remover a FK `Deck.note_type` (obrigatória, hoje `on_delete=PROTECT`). O conjunto de
tipos de nota de um deck passa a ser **derivado** das notas que já pertencem a ele
(`NoteType.objects.filter(notes__deck=deck).distinct()`), sem tabela de junção nova.

**Rationale**: `Note.note_type` já é uma FK própria e independente da FK do deck desde o MVP
(`backend/apps/notes/models.py:31-33`, documentado em `specs/001-ankihub-brasil-mvp/data-model.md:75`
como relação separada da linha 38 de `Deck.note_type`). Uma nota nunca migra de deck nem de tipo de
nota depois de criada (sync é unidirecional, create-only), então `notes→note_type` já é a fonte da
verdade sem risco de desalinhamento — adicionar uma M2M `Deck↔NoteType` duplicaria essa informação e
criaria uma segunda fonte de verdade para manter sincronizada.

**Alternatives considered**:
- Manter `Deck.note_type` como "tipo primário/de exibição" — rejeitado: ambíguo assim que o deck é
  legitimamente multi-tipo (qual tipo é "o principal"? isso não tem resposta de negócio).
  M2M explícita `Deck↔NoteType` — rejeitado: redundante com `Note.note_type`, mais uma tabela para
  manter consistente sem ganho (nenhum caso de uso precisa de um tipo de nota "no deck" sem nenhuma
  nota daquele tipo).

## Decisão 2 — Contrato de publish (upload) para múltiplos tipos de nota

**Decision**: o payload de `POST /decks/{id}/publish/` passa a enviar `note_types: list[dict]` (era
`note_type: dict` único) e cada item de `notes` ganha `note_type_index: int`, referenciando a posição
do seu tipo de nota dentro dessa lista. O backend cria um `NoteType` por item da lista, dentro da mesma
transação atômica já existente, e resolve a FK de cada `Note` pelo índice.

**Rationale**: replica a forma que o caminho de leitura **já usa** — `sync/full` e `sync/delta` já
mandam `note_types: list[dict]` e cada nota carrega `note_type_id` (`backend/apps/sync/views.py:78-101`
`_note_type_payload`/`_note_payload`), e o add-on já sabe consumir essa lista + resolver por ID
(`addon/ankihub_br/main/sync.py:64-113,163`, `models_by_remote_id[item["note_type_id"]]`). O publish é
o único lado assimétrico hoje. Usar **índice** em vez de nome evita o caso de borda do spec (dois
tipos de nota podem ter o mesmo nome e estruturas diferentes — o Anki os distingue por ID interno, não
por nome); no momento do publish o backend ainda não tem um ID remoto para o tipo de nota (ele nasce
nessa mesma transação), então índice posicional é a chave de correlação mais simples que não exige
inventar um ID cliente-side.

**Alternatives considered**:
- Correlacionar por nome do tipo de nota — rejeitado, ver o caso de borda de nomes duplicados no spec
  (`spec.md` → Edge Cases).
- Add-on gerar um UUID client-side por tipo de nota — rejeitado, complexidade desnecessária (YAGNI);
  índice posicional dentro de uma única lista de uma única requisição é suficiente e mais simples.

## Decisão 3 — Gatilho de ressincronização completa por mudança estrutural (FR-008/FR-035 do MVP)

**Decision**: `DeltaView` passa a checar
`NoteType.objects.filter(notes__deck=deck, structure_changed_at__gt=since).exists()` em vez de ler
`deck.note_type.structure_changed_at` diretamente.

**Rationale**: mantém a semântica exata já documentada em FR-035 (mudança estrutural em **qualquer**
tipo de nota do deck força full resync), só trocando a fonte de leitura de "o tipo de nota único do
deck" para "qualquer tipo de nota tocado pelas notas do deck". Um único JOIN indexado
(`notes(deck, mod)` já indexado; `note_type_id` é FK indexada por padrão) — sem necessidade de
denormalizar nada no `Deck`.

**Alternatives considered**: denormalizar um campo `Deck.notetypes_changed_at` atualizado por sinal —
rejeitado como otimização prematura (YAGNI); volume de decks/tipos de nota no MVP não justifica.

## Decisão 4 — Validação de nomes de campo (proteção e sugestões)

**Decision**:
- **Proteção de campo** (`ProtectionConfigSerializer.validate_fields`, deck-wide por natureza — não
  há conceito de "proteção por tipo de nota" no produto): validar contra a **união** dos
  `field_names` de todos os tipos de nota distintos do deck.
- **Sugestão de mudança** (individual e em lote): validar `proposed_field_values` contra o
  `field_names` do **tipo de nota da própria nota-alvo**, não mais `deck.note_type`. Sugestão em lote
  (`bulk-change`) passa a exigir que todas as notas-alvo compartilhem o mesmo tipo de nota — uma
  mesma proposta de campos só faz sentido semântico aplicada a notas estruturalmente iguais; decks
  multi-tipo simplesmente não podiam colidir nisso antes porque só existia um tipo de nota por deck.
- **Sugestão de nota nova** (`new-note`): passa a exigir a escolha de **um dos tipos de nota já
  existentes no deck** (novo campo `note_type` na sugestão), **exceto** quando o deck tem exatamente
  um tipo de nota — nesse caso o campo é opcional e o backend resolve automaticamente para o único
  tipo existente, preservando FR-010/SC-003 (zero mudança de comportamento observável em decks já
  publicados com um único tipo). `400` se omitido em deck com 2+ tipos, ou se o valor enviado não
  pertencer ao deck. Criar um tipo de nota inteiramente novo a partir de uma sugestão fica fora de
  escopo (seria uma superfície de moderação nova, não pedida).

**Rationale**: proteção de campo é uma preferência por **nome de campo** configurada uma vez por
usuário/deck (`backend/apps/protection/models.py`, sem referência a tipo de nota) — manter a união é a
extensão mínima que preserva o comportamento observável de hoje (usuário continua protegendo "Front"
uma vez só). Sugestões, ao contrário, sempre validaram contra a estrutura real de uma nota específica;
usar `deck.note_type` era só um atalho válido enquanto havia exatamente um tipo por deck — restaurar a
nota como fonte da verdade é o comportamento correto, não uma mudança de política.

**Alternatives considered**: manter união de campos também para sugestões de mudança — rejeitado,
silenciosamente incorreto assim que dois tipos de nota do deck têm campos com o mesmo nome mas
significado diferente, e quebra a confiança do moderador de que uma sugestão aceita realmente bate com
o template real daquela nota.

## Decisão 5 — Add-on: remoção da guarda de tipo único

**Decision**: em `addon/ankihub_br/main/publish.py`, remover o `if len(notetype_ids) != 1: raise
PublishError(...)`, agrupar as notas exportadas por `note.mid`, construir um `note_type` por grupo (na
ordem de primeira ocorrência) e gravar o índice de cada grupo em cada nota exportada como
`note_type_index`.

**Rationale**: é a reversão direta da restrição documentada como MVP-only em
`specs/001-ankihub-brasil-mvp/data-model.md:38` e cuja mensagem de erro foi apenas melhorada (não
removida) no bug `multi-notetype-import-error` — esta feature é a extensão pós-MVP que aquele bugfix
já antecipava.

**Alternatives considered**: nenhuma — é remoção de guarda + payload já desenhado na Decisão 2.

## Decisão 6 — Exposição da composição de tipos de nota no detalhe do deck (US3/FR-009)

**Decision**: `DeckDetailSerializer.get_note_type` (singular) é substituído por
`get_note_types` retornando uma lista `[{id, name, field_names, note_count}]`, com `note_count`
calculado em uma única query agregada (`Note.objects.filter(deck=deck,
deleted_at__isnull=True).values("note_type").annotate(count=Count("id"))`) — sem N+1.

**Rationale**: é o dado mínimo que a US3 pede (lista de tipos + contagem por tipo), reaproveitando o
padrão de `SerializerMethodField` já usado no mesmo serializer para `moderator_count`/`is_moderator`.

**Alternatives considered**: endpoint dedicado `/decks/{id}/note-types/` — rejeitado, YAGNI; é uma
lista pequena e barata o bastante para caber no detalhe do deck que a US3 já teria que abrir de
qualquer forma.
