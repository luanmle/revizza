# Bug Fix: Avatar upload always fails with generic error message

- **Slug**: avatar-upload-fails
- **Fixed**: 2026-07-15
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

Wrapped the Supabase Storage calls in `MeView.patch` in `try/except`, so a missing bucket or a
storage-service failure now returns a clean `400 {"avatar": [...]}` instead of an unhandled 500 —
the frontend's existing error handling already renders that field error correctly. Added
`provision_avatars_bucket` to the Heroku `release` phase so the bucket is created/kept public on
every deploy instead of depending on someone remembering to run it manually. The immediate
production fix (bucket didn't exist) is an ops action, not a code change — flagged separately
below, not yet executed.

## Changes

| File | Change | Notes |
|------|--------|-------|
| `backend/apps/accounts/views.py` | modified | `MeView.patch`: `avatars.upload` failure → `400` with `{"avatar": [...]}` (old avatar untouched); `avatars.delete` on removal failure → `400`, `avatar_path` untouched; `avatars.delete` of the *old* path after a successful new upload is now best-effort (swallowed) since the new avatar already persisted |
| `backend/Procfile` | modified | `release` phase now also runs `provision_avatars_bucket`, mirroring `migrate`'s always-run pattern |
| `backend/tests/contract/test_accounts_me.py` | added tests | storage-upload-failure and storage-delete-failure cases, pinning the 400-not-500 contract |

## Diff Highlights

```python
# backend/apps/accounts/views.py
old_path = request.user.avatar_path
try:
    new_path = avatars.upload(request.user.id, content, ext)
except Exception:  # bucket ausente, Storage fora do ar etc.
    return Response(
        {"avatar": ["Não foi possível salvar a imagem, tente novamente."]},
        status=status.HTTP_400_BAD_REQUEST,
    )
```

```
# backend/Procfile
release: python manage.py migrate --noinput && python manage.py createcachetable && python manage.py check_data_api_isolation && python manage.py provision_avatars_bucket
```

## Tests Added or Updated

- `backend/tests/contract/test_accounts_me.py::test_patch_me_returns_clean_error_when_storage_upload_fails` — monkeypatches `avatars.upload` to raise, asserts `400` + `avatar` field error + `avatar_path` stays `None`.
- `backend/tests/contract/test_accounts_me.py::test_patch_me_returns_clean_error_when_storage_delete_fails` — uploads a real (fake-storage) avatar, then monkeypatches `avatars.delete` to raise on removal, asserts `400` + `avatar_path` unchanged (FR-003).

## Local Verification

- Commands run: `.venv/bin/python -m pytest tests/ -q` → **245 passed** (was 243 before this fix; +2 new tests, no regressions).
- Manual checks: none against production (see Follow-ups — the production bucket-provisioning step itself was not run as part of this fix, per the safety protocol around live-infrastructure changes).

## Deviations from Assessment

None — implemented exactly the "Preferred" remediation from the assessment (try/except hardening
+ Procfile release-phase wiring + regression tests). The assessment's immediate/ops step (running
`provision_avatars_bucket` against production right now) was intentionally **not** executed here;
see Follow-ups.

## Follow-ups

- **Run now, with explicit confirmation**: `heroku run python manage.py provision_avatars_bucket -a revizza-api` — this is the actual unblock for the currently-broken production upload flow. The code fix prevents a *future* recurrence (clean 400 instead of 500) and self-heals on the *next* deploy via the Procfile change, but today's bucket-less state in production is still broken until either this command runs manually or a new deploy fires the updated `release` phase.
- Consider the same `try/except` hardening isn't needed elsewhere for `avatars.public_url` (read path) — it doesn't hit the network (pure string construction from a public-bucket URL pattern), so no equivalent failure mode exists there.
