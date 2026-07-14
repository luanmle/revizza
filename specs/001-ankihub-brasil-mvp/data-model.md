# Data Model: AnkiHub Brasil — MVP

Escopo: entidades do backend (Postgres via Supabase, fonte da verdade) e, em seção separada, as
entidades que vivem apenas no cliente (cache local do add-on). Os nomes de campo priorizam clareza
sobre a entidade, não os nomes exatos de coluna que a implementação vai usar.

Convenção geral: todo modelo tem `id` (UUID), `created_at`/`updated_at`; omitidos abaixo por brevidade
exceto quando o timestamp tem significado de negócio (ex. `mod` de uma nota, usado no delta de sync).

## Entidades do backend

### User
Estende o usuário gerenciado pelo Supabase Auth com os dados de perfil específicos do produto.

| Campo | Tipo | Notas |
|---|---|---|
| `auth_id` | UUID | referência ao usuário no Supabase Auth; chave de junção, não gerada aqui |
| `email` | string | espelhado do Auth para consultas locais |
| `name` | string, opcional | nome exibido em sugestões e comentários; nunca substituído pelo e-mail |
| `target_career` | enum (`fiscal`/`policial`/`juridica`/`outra`/null) | opcional, onboarding (US-01) |
| `target_board` | string, nullable | banca/edital de interesse (US-01) |
| `consent_marketing_emails` | bool, default `false` | nunca pré-marcado (FR-005) |
| `consent_research_data` | bool, default `false` | nunca pré-marcado (FR-005) |
| `is_suspended` | bool, default `false` | soft-ban reversível (FR-049) |
| `deletion_requested_at` | timestamp, nullable | início da carência de 7 dias (FR-046) |

**Transições**: `deletion_requested_at` nulo → preenchido (usuário pede exclusão) → nulo novamente
(usuário desiste dentro do prazo) **ou** registro anonimizado e desvinculado após 7 dias (job de
limpeza, fora do escopo de UI). `is_suspended` alterna `false` ⇄ `true` apenas por ação de
administrador (FR-049).

### Deck
| Campo | Tipo | Notas |
|---|---|---|
| `name` | string | |
| `description` | text | |
| `subject_tags` | lista de string | usado no filtro do catálogo (FR-007) |
| `note_type` | FK → NoteType | um deck usa um tipo de nota (pode ser estendido a N no pós-MVP) |
| `note_count` | int, denormalizado | atualizado ao criar/remover nota |
| `subscriber_count` | int, denormalizado | atualizado ao (des)inscrever |

**Importação inicial (FR-062, clarificado 2026-07-14)**: `Deck` + `NoteType` + `Note`s commitam em uma
única transação atômica no `publish` — o deck nunca aparece parcialmente publicado no catálogo. Upload
de mídia roda fora dessa transação em melhor esforço; falha isolada de mídia não desfaz a publicação
(fica pendente até uma sincronização subsequente trazer o arquivo — ver `contracts/sync.md`).

### DeckModerator
Junção usuário↔deck com papel de moderador (US-11).

| Campo | Tipo | Notas |
|---|---|---|
| `deck` | FK → Deck | |
| `user` | FK → User | |
| `invited_by` | FK → User, nullable | nulo para o moderador original/criador |
| `status` | enum (`pending`, `active`) | convite aguardando aceite vs. moderador ativo |

**Regra de invariante**: um `Deck` nunca pode ficar com zero `DeckModerator` em status `active`
(FR-030) — validado na camada de aplicação antes de permitir remoção.

### NoteType (mapeia `notetypes`/`models` do Anki)
| Campo | Tipo | Notas |
|---|---|---|
| `name` | string | ex. "Básico", "Cloze Jurídico" |
| `field_names` | lista ordenada de string | ordem preservada — nova versão nunca reordena campos existentes (US-08 AC) |
| `templates` | JSON | um item por template de card (frente/verso), mapeando `templates` nativo |
| `css` | text | mapeia `col`/CSS nativo do tipo de nota |

**Transição estrutural sensível**: alteração no número de `templates` é o gatilho documentado para
forçar ressincronização completa em vez de delta parcial (FR-035).

### Note (mapeia `notes`/`cards` do Anki)
| Campo | Tipo | Notas |
|---|---|---|
| `deck` | FK → Deck | |
| `note_type` | FK → NoteType | |
| `field_values` | JSON `{nome_campo: html_sanitizado}` | HTML já passou por `nh3` antes de chegar aqui (FR-015) |
| `tags` | lista de string | |
| `guid` | string | identificador estável compatível com o formato de GUID do Anki |
| `mod` | timestamp | atualizado a cada mudança aceita; é o marcador usado pelo delta de sync (FR-034) |
| `deleted_at` | timestamp, nullable | soft-delete — permite propagar remoção (US-07) sem perder auditoria |

### Subscription
| Campo | Tipo | Notas |
|---|---|---|
| `user` | FK → User | |
| `deck` | FK → Deck | |
| `sync_trigger_manual` | bool, default `true` | US-08: gatilhos configuráveis, não mutuamente exclusivos |
| `sync_trigger_on_anki_open` | bool, default `false` | |
| `sync_trigger_chained_native` | bool, default `false` | encadeado antes do sync nativo do Anki |
| `delete_notes_on_removal` | bool, default `false` | preferência local: apagar de fato vs. apenas marcar (FR-037) |

### Suggestion
| Campo | Tipo | Notas |
|---|---|---|
| `type` | enum (`change`, `new_note`, `deletion`) | três categorias distintas (US-05/06/07) |
| `deck` | FK → Deck | |
| `author` | FK → User | |
| `change_category` | enum (`conteudo_atualizado`, `ortografia_gramatica`, `erro_conteudo`, `nova_tag`, `tag_atualizada`, `outro`), nullable | obrigatório apenas quando `type=change` (FR-013) |
| `justification` | text | obrigatória em todos os tipos |
| `proposed_field_values` | JSON, nullable | usado em `change`/`new_note` |
| `status` | enum (`pending`, `accepted`, `rejected`) | terminal ao sair de `pending` — sem reversão via UI (FR-027). Decisão (accept/reject) usa `select_for_update()` dentro da transação: a primeira decisão commitada vence, uma segunda tentativa concorrente relê o status já terminal e falha sem sobrescrever (FR-027, clarificado 2026-07-14) |
| `rejection_reason` | text, nullable | |
| `decided_by` | FK → User, nullable | moderador que decidiu |

### SuggestionTargetNote
Junção que permite uma única `Suggestion` de tipo `change` cobrir várias notas (sugestão em lote,
FR-017).

| Campo | Tipo | Notas |
|---|---|---|
| `suggestion` | FK → Suggestion | |
| `note` | FK → Note | |

### SuggestionVote
| Campo | Tipo | Notas |
|---|---|---|
| `suggestion` | FK → Suggestion | |
| `user` | FK → User | |
| `value` | enum (`like`, `dislike`) | unique(`suggestion`, `user`) — um voto por usuário por sugestão |

### Comment
Comentário geral em nota (US-04) ou específico de uma sugestão (US-09) — nunca ambos ao mesmo
tempo, por isso as duas threads nunca se misturam (spec FR-024).

| Campo | Tipo | Notas |
|---|---|---|
| `author` | FK → User | |
| `body` | text | |
| `note` | FK → Note, nullable | preenchido apenas na thread geral da nota |
| `suggestion` | FK → Suggestion, nullable | preenchido apenas na thread da sugestão |
| `edited_at` | timestamp, nullable | |

**Invariante**: exatamente um entre `note` e `suggestion` é não nulo (constraint de aplicação/DB).

### Report
| Campo | Tipo | Notas |
|---|---|---|
| `reporter` | FK → User | |
| `comment` | FK → Comment | conteúdo denunciado (US-14) |
| `reason` | text, nullable | |
| `status` | enum (`pending`, `reviewed`) | |
| `reviewed_by` | FK → User, nullable | administrador da plataforma |

### ProtectedFieldConfig / ProtectedTagConfig
Configuração por assinante+deck (US-12); aplicada a todas as notas do deck por padrão.

| Campo | Tipo | Notas |
|---|---|---|
| `user` | FK → User | |
| `deck` | FK → Deck | |
| `field_name` (ProtectedFieldConfig) / `tag_pattern` (ProtectedTagConfig) | string | correspondência de texto |

Proteção pontual por nota (tag `AnkiHubBR_Protect::<Campo>`) não tem tabela própria — é lida
diretamente das `tags` da `Note`/da coleção local pelo add-on, nunca persistida como configuração
separada.

### MediaFile
| Campo | Tipo | Notas |
|---|---|---|
| `deck` | FK → Deck | |
| `content_hash` | string (sha256) | evita reenviar/rebaixar arquivo inalterado (FR-036) |
| `storage_path` | string | caminho no Supabase Storage |
| `original_filename` | string | |

## Entidades locais do add-on (fora do Postgres)

Vivem apenas no `user_files/` do add-on, via `peewee`+SQLite, nunca replicadas ao backend
(ver research.md §4). Existem para permitir o cálculo do delta a cada sincronização.

### SyncStateCache
| Campo | Tipo | Notas |
|---|---|---|
| `deck_id` | string | referência ao Deck remoto |
| `note_id` | string | referência à Note remota |
| `last_seen_mod` | timestamp | último `mod` aplicado localmente |
| `last_update_type` | enum (`created`, `updated`, `deleted`) | |

## Relações entre entidades (visão resumida)

```text
User ──< Subscription >── Deck ──< DeckModerator >── User
Deck ──1:1── NoteType ──< Note
Note ──< SuggestionTargetNote >── Suggestion ── author: User
Suggestion ──< SuggestionVote >── User
Suggestion ──< Comment (via suggestion FK) ── author: User
Note ──< Comment (via note FK) ── author: User
Comment ──< Report ── reporter: User, reviewed_by: User
User ──< ProtectedFieldConfig/ProtectedTagConfig >── Deck
Deck ──< MediaFile
```
