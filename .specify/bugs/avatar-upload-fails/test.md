# Bug Verification: Avatar upload always fails with generic error message

- **Slug**: avatar-upload-fails
- **Tested**: 2026-07-15
- **Assessment**: ./assessment.md
- **Fix**: ./fix.md
- **Result**: partial

## Summary

The fix's own regression tests pass and prove the code-level defect (unhandled `avatars.upload`/
`avatars.delete` exceptions turning into a 500) is closed: a simulated storage failure now returns
a clean `400 {"avatar": [...]}` with the prior avatar state untouched. However, the **original
production symptom was not re-reproduced end-to-end** — the `avatars` bucket has not been
provisioned in production and no new deploy has fired the updated `Procfile` release phase, so a
real upload against the live app has not been re-attempted. Marked `partial`, not `verified`.

## Checks Performed

| Check | Command / Action | Result | Notes |
|-------|------------------|--------|-------|
| Reproduction (post-fix, production) | manual upload on `/account` against deployed app | not-run | Requires either running `provision_avatars_bucket` against prod or a new deploy — neither executed; user had not yet confirmed the live-infra step as of this check |
| New tests (storage-upload-failure) | `pytest tests/contract/test_accounts_me.py -k storage_upload_fails` | pass | `400`, `avatar` field error, `avatar_path` stays `None` |
| New tests (storage-delete-failure) | `pytest tests/contract/test_accounts_me.py -k storage_delete_fails` | pass | `400`, `avatar` field error, `avatar_path` unchanged (FR-003) |
| Full regression suite | `pytest tests/ -q` | pass | 245 passed, 0 failed (was 243 pre-fix; +2 new) |
| Lint | `ruff check apps/accounts/views.py apps/accounts/avatars.py` | pass | no issues |
| Procfile sanity | `python manage.py provision_avatars_bucket --help` | pass | command resolves under the exact invocation added to `Procfile`'s release line |

## Output Excerpts

```
tests/contract/test_accounts_me.py ..                                    [100%]
2 passed, 12 deselected in 1.14s
```

```
245 passed, 6 warnings in 10.74s
```

```
All checks passed!
```

## Residual Risks

- **Production is likely still broken right now.** The code fix changes *how* a storage failure
  surfaces (clean 400 vs. 500) and the `Procfile` change makes future deploys self-provision the
  bucket — but neither has actually created the `avatars` bucket in the live Supabase project yet.
  Until a new deploy runs (or `heroku run python manage.py provision_avatars_bucket -a revizza-api`
  is run manually), a real user upload against production will still fail — now with a slightly
  more honest-sounding but still generic message ("Não foi possível salvar a imagem, tente
  novamente."), because `avatars.upload` will still raise on the missing bucket.
- No staging environment was used to verify the full deploy → release-phase → bucket-created →
  upload-succeeds chain; this was reasoned about from `Procfile` and command behavior, not
  observed end-to-end.

## Recommendation

Hold — do not close the bug yet. The code changes are verified correct by the test suite and are
safe to ship, but the reported symptom will keep reproducing in production until the bucket is
actually provisioned there (either by running `provision_avatars_bucket` manually now, or by
deploying so the updated `Procfile` release phase runs it). Once that ops step happens, re-run
this verification against the live app to confirm the original symptom is gone, then mark
`verified`.
