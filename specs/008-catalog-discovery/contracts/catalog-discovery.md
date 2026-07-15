# Contract: Catalog Discovery

Extends the existing catalog contract without adding endpoints.

## GET `/api/v1/decks/`

Lists decks with cursor pagination.

### Query parameters

| Name | Values | Notes |
|---|---|---|
| `tag` | string | Existing tag filter; combines with personal filters and sort. |
| `subscribed` | truthy/absent | Existing filter. When truthy, returns decks subscribed by current user. |
| `moderated` | truthy/absent | New filter. When truthy, returns decks actively moderated by current user. |
| `sort` | `recommended`, `popular`, `updated`, `notes`, `recent` | Defaults to `recommended`. |
| `cursor` | opaque string | Pagination cursor from previous response. Must be reset when tag/filter/sort changes. |

`subscribed` and `moderated` are mutually exclusive for the web tabs. If both are sent, API should
prefer a validation error over guessing.

### Sort mapping

| Public value | Meaning | Stable order |
|---|---|---|
| `recommended` | recommended first, then popular/recent | recommended desc, subscriber count desc, created at desc, id desc |
| `popular` | most subscribers first | subscriber count desc, created at desc, id desc |
| `updated` | newest content first | last updated at desc, created at desc, id desc |
| `notes` | most notes first | note count desc, created at desc, id desc |
| `recent` | newest published first | created at desc, id desc |

### Response item

```json
{
  "id": "uuid",
  "name": "Direito Constitucional",
  "description": "Resumo curto do deck",
  "subject_tags": ["Direito Constitucional"],
  "note_count": 120,
  "subscriber_count": 45,
  "created_at": "2026-07-15T10:00:00Z",
  "last_updated_at": "2026-07-15T12:00:00Z",
  "is_official": true,
  "creator": {
    "id": "uuid",
    "name": "Ana Silva",
    "avatar_url": "https://..."
  }
}
```

When `subscribed=1`, existing subscription fields remain in the response for add-on compatibility.

## GET `/api/v1/decks/{id}/`

Returns existing deck detail plus discovery trust fields.

### Additional response fields

```json
{
  "last_updated_at": "2026-07-15T12:00:00Z",
  "is_official": true,
  "creator": {
    "id": "uuid",
    "name": "Ana Silva",
    "avatar_url": "https://..."
  },
  "moderators": [
    {
      "id": "moderator-relation-uuid",
      "user_id": "uuid",
      "name": "Bruno Costa",
      "avatar_url": "https://..."
    }
  ]
}
```

Only active moderators appear in `moderators`.

## Frontend UI contract

- `/decks` renders three tabs: "Catálogo", "Meus baralhos", "Inscritos".
- Anonymous users can use "Catálogo"; personal tabs show login-oriented empty/blocked state.
- Sort select offers: "Recomendados", "Mais populares", "Atualizados recentemente", "Mais notas",
  "Recentes".
- Cards show official badge, creator avatar/name, relative updated time, note count, subscriber count,
  and tags.
- `/decks/[id]` shows official badge, creator avatar/name, relative updated time, and active moderator
  avatars.
- Tag, tab, and sort state are reflected in the URL so the view can be shared or refreshed.
