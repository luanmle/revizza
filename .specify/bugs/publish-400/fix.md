# Bug Fix: publish 400 — realinhar backend com contrato multi-notetype do add-on

- **Slug**: publish-400
- **Fixed**: 2026-07-14
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

O bug era version skew de release, não defeito de código: o add-on já enviava `note_types[]`, mas a
`main` (deploy Heroku) ainda esperava `note_type` singular e respondia `400`. A correção é operacional —
a feature `002-multi-notetype-decks` (que já tinha o backend correto) foi merjada na `main` e pushada.
O deploy no Heroku + `migrate` continua pendente (sem creds/remote Heroku neste ambiente).

## Changes

| File | Change | Notes |
|------|--------|-------|
| (nenhum arquivo de código editado) | — | fix é merge de release, não patch |
| `main` (git) | merge `--no-ff` de `002-multi-notetype-decks` | commit `8126c30`, pushado para `origin/main` |

O merge trouxe o backend correto que já existia na branch:
- `backend/apps/sync/views.py` — `PublishView.post` lê `data.get("note_types")` (lista)
- `backend/apps/catalog/migrations/0004_remove_deck_note_type.py`
- `backend/apps/suggestions/migrations/0005_suggestion_note_type.py`

## Diff Highlights (optional)

Contrato do backend antes (rejeitava o payload novo) vs depois do merge:

```python
# antes (main pré-merge):  note_type singular → 400 com payload do add-on novo
note_type_data = data.get("note_type") or {}
if not data.get("name") or not note_type_data.get("field_names"):
    return 400 "Payload requer name e note_type.field_names."

# depois (main pós-merge): note_types lista, alinhado ao add-on
note_types_data = data.get("note_types") or []
if not data.get("name") or not note_types_data or any(not nt.get("field_names") ...):
    return 400 "Payload requer name e note_types[] com field_names."
```

## Tests Added or Updated

- Nenhum teste novo neste passo — a suíte da feature 002 já cobre o contrato:
  `backend/tests/contract/test_sync_publish.py` (multi-item, índice inválido, atomicidade).

## Local Verification

- `cd backend && pytest apps/sync tests/contract/test_sync_publish.py -q` → **8 passed** (na `main` já
  merjada).
- Merge: `git merge --no-ff 002-multi-notetype-decks` → sem conflitos; `git push origin main` →
  `c82678d..8126c30`.

## Deviations from Assessment

Nenhuma. O assessment previu remediação de release sem edição de código-fonte; foi exatamente isso.
Status `partial` (não `applied`) porque o deploy — a metade que efetivamente conserta produção — depende
de acesso ao Heroku que não existe neste ambiente.

## Deploy

- Workflow `.github/workflows/deploy.yml` disparado automaticamente pelo push na `main`.
- Run `29362651040` → **success** (test → build imagens web/release → `heroku container:release`).
- Imagem `release` rodou `migrate --noinput && createcachetable && check_data_api_isolation`
  (Procfile) antes de promover a web — job release verde = migração aplicada sem erro.
- App: `revizza-api` (`https://revizza-api-37fd874aff98.herokuapp.com`).

## Follow-ups

- Validar em produção com um publish real (deck tipo único SC-003 + deck misto SC-001) —
  `/speckit-bug-test slug=publish-400`.
- Validar em produção com um publish real de deck de tipo único (SC-003) e de deck misto (SC-001) —
  ver `specs/002-multi-notetype-decks/quickstart.md` Cenários 1 e 4.
- Considerar automatizar o `migrate` no release do Heroku (`release:` no Procfile) para evitar skew
  schema↔código em deploys futuros.
