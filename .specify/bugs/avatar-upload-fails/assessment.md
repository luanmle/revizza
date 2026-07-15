# Bug Assessment: Avatar upload always fails with generic error message

- **Slug**: avatar-upload-fails
- **Created**: 2026-07-15
- **Source**: pasted text
- **Verdict**: valid
- **Severity**: high

## Report (verbatim or summarized)

> "Não foi possível enviar a foto." essa mensagem aparece quando tento carregar uma foto de perfil

User reports the generic frontend error message appears every time they try to upload a profile
photo on `/account`.

## Symptom

Uploading a profile photo (any file, presumably valid JPEG/PNG/WebP under 5MB) on `/account`
always fails, surfacing the frontend's generic fallback string "Não foi possível enviar a foto."
instead of a specific validation error or a success. Expected: valid images upload successfully
and render as the new avatar.

## Reproduction

1. Log in on the deployed web app (`https://revizza-web-a43d443ee5e7.herokuapp.com`, or local
   dev pointed at the deployed backend).
2. Go to `/account`.
3. Choose a valid JPEG/PNG/WebP file under 5MB in the avatar file input.
4. Observe: generic error message, no avatar saved.

[NEEDS CLARIFICATION: exact environment (prod web app vs. local frontend against prod/local
backend) and browser devtools network response body/status for the failed `PATCH
/accounts/me/` request — would confirm 500 vs. a network-level failure.]

## Suspected Code Paths

- `backend/apps/accounts/views.py:77` — `avatars.upload(request.user.id, content, ext)` is
  called with no `try/except`. Any exception raised by the Supabase Storage client (bucket
  missing, network error, auth/service-role issue) propagates unhandled out of `MeView.patch`,
  producing a DRF 500 response whose JSON body has no `"avatar"` key.
- `frontend/src/app/account/page.tsx` (`uploadAvatar` mutation `onError`) — falls back to the
  generic "Não foi possível enviar a foto." string whenever the error body isn't
  `{"avatar": [...]}` (a network-level fetch failure, or any non-`{"avatar": ...}` JSON body such
  as a 500 or a 401). This is exactly what would happen after an unhandled `avatars.upload`
  exception, and also masks the *actual* server-side reason from the user.
- `backend/Procfile:2` — the Heroku `release` phase runs `migrate`, `createcachetable`, and
  `check_data_api_isolation` only. It does **not** run
  `python manage.py provision_avatars_bucket`. That command
  (`backend/apps/sync/management/commands/provision_avatars_bucket.py`, added in feature 007) is
  a manual one-off step documented only in `specs/007-profile-edit-avatar/quickstart.md` — there
  is no evidence it was ever run against the production Supabase project after the 007 deploy
  (`git push origin main` → Heroku auto-deploy, release v20, ~2026-07-15T02:23:48Z).

## Root Cause Hypothesis

**Confidence: high.** The `avatars` bucket was very likely never provisioned in the production
Supabase Storage project — `provision_avatars_bucket` is a manual command, not part of the
Heroku release phase, and nothing else in the deploy path calls it. When a user uploads a valid
image, `avatars.upload()` (`backend/apps/accounts/avatars.py`) calls
`_storage().from_(BUCKET).upload(...)` against a bucket that doesn't exist, the Supabase Storage
client raises, and that exception is unhandled in `MeView.patch`, turning into a 500. The
frontend's `onError` handler can't find an `"avatar"` key in a 500's body and falls back to the
generic string — which is why the message shows regardless of what file the user picks.

A secondary, lower-likelihood contributor: `MeView.patch` has no defensive handling around
`avatars.upload`/`avatars.delete` at all, so even after the bucket exists, any transient Supabase
Storage failure will surface as the same unhelpful generic message instead of the "clear error"
the spec's edge case requires (spec.md Edge Cases: "Falha de rede/serviço de storage durante o
upload: usuário recebe mensagem de erro clara").

CORS was considered and ruled unlikely: `DJANGO_CORS_ALLOWED_ORIGINS` in production already
includes the deployed frontend origin, so a same-origin request from the real web app wouldn't be
blocked.

## Proposed Remediation

**Preferred**: Two-part fix.

1. **Immediate/ops**: run `heroku run python manage.py provision_avatars_bucket -a revizza-api`
   once against production to create the bucket. This alone likely resolves the reported symptom.
2. **Code hardening** (prevents recurrence and satisfies the spec's edge case): wrap the
   `avatars.upload`/`avatars.delete` calls in `MeView.patch` in a `try/except`, mirroring the
   pattern already used in `RegisterView.post` for `supabase_gateway.sign_up` — catch storage
   exceptions and return `400`/`503` with `{"avatar": ["Não foi possível salvar a imagem, tente novamente."]}`
   so the frontend's existing `body?.avatar?.[0]` path renders a real (if generic-at-the-network-level)
   message instead of falling through to a raw 500. Additionally, wire
   `provision_avatars_bucket` into the Heroku `release` phase in `backend/Procfile` (alongside
   `migrate`), same as `provision_media_bucket` arguably should be, so bucket provisioning is
   never again a manual step someone can forget after a deploy.

**Alternatives**:
- Leave provisioning manual but add a startup/health check that fails loudly (e.g. Django system
  check) if the `avatars` bucket doesn't exist — more visible than a Procfile line, but doesn't
  self-heal like running the command in `release` does.

**Files likely to change**:
- `backend/Procfile` (add `provision_avatars_bucket` to `release`)
- `backend/apps/accounts/views.py` (`MeView.patch` — try/except around `avatars.upload`/`delete`)
- `backend/tests/contract/test_accounts_me.py` (new case: storage exception → clean error
  response, not a 500)

**Tests to add or update**:
- Contract test: monkeypatch `avatars.upload` to raise, PATCH with a valid image, assert `400`
  (or `503`) with an `"avatar"` field error, not an unhandled 500.
- Unit/ops check (optional): a smoke test or manual verification that `provision_avatars_bucket`
  is idempotent when run repeatedly in `release` (already covered by
  `backend/tests/unit/test_avatars_bucket.py`'s no-op case).

## Risks & Considerations

- Running `provision_avatars_bucket` against production is safe/idempotent (mirrors
  `provision_media_bucket`'s pattern, already unit-tested for the create/no-op/flip cases) but is
  still a live-infrastructure change — should be confirmed with the user before executing, not
  run silently as part of this assessment.
- Adding the command to the Heroku `release` phase makes every future deploy depend on Supabase
  Storage being reachable at release time; if Supabase has a transient outage during a deploy,
  the release (and thus the whole deploy) would fail. Acceptable trade-off given `migrate` already
  has the same dependency on Supabase Postgres being reachable.
- The generic frontend fallback message will still appear for genuine network failures (client-side
  offline, CORS misconfiguration elsewhere) after the fix — that's correct per spec's edge case,
  just currently mislabeled because the real cause was a missing bucket, not a network blip.

## Open Questions

- [NEEDS CLARIFICATION: has anyone confirmed via Supabase dashboard or `heroku run python manage.py shell` that the `avatars` bucket doesn't exist in production? This assessment infers it from the deploy path, not a direct check.]
- [NEEDS CLARIFICATION: browser devtools network tab response status/body for the failed request, to confirm 500 vs. some other failure mode.]
