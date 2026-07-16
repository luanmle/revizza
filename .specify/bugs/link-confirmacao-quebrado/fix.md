# Bug Fix: Link de confirmação de e-mail quebrado

- **Slug**: link-confirmacao-quebrado
- **Fixed**: 2026-07-15
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

O cadastro agora envia explicitamente ao Supabase o redirect `/verify-email`, e o frontend possui uma rota que valida o callback de confirmação. A URL é configurável e usa `FRONTEND_BASE_URL/verify-email` por padrão.

## Changes

| File | Change | Notes |
|------|--------|-------|
| `backend/apps/accounts/supabase_gateway.py` | modified | Passa `options.email_redirect_to` ao `sign_up`. |
| `backend/config/settings/base.py` | modified | Adiciona `EMAIL_CONFIRMATION_REDIRECT_URL` com fallback seguro. |
| `backend/.env.example` | modified | Documenta a variável opcional. |
| `frontend/src/app/(auth)/verify-email/page.tsx` | added | Valida `token_hash`/`type` via `verifyOtp` e mostra estados de sucesso/erro. |
| `backend/tests/unit/test_supabase_gateway.py` | added | Garante que o redirect correto é enviado ao Supabase. |

## Tests Added or Updated

- `backend/tests/unit/test_supabase_gateway.py::test_sign_up_passes_email_confirmation_redirect` — fixa o payload de cadastro e impede regressão do redirect.
- `backend/tests/contract/test_accounts_register.py` — testes existentes continuam passando.

## Local Verification

- Commands run: `backend/.venv/bin/pytest -q tests/unit/test_supabase_gateway.py tests/contract/test_accounts_register.py` → `6 passed`.
- Commands run: `npm run test -- --run` → `14 passed`.
- Commands run: `npm run lint` → pass.
- Commands run: `npm run build` → pass; `/verify-email` foi incluída nas rotas geradas.
- Manual checks: não executados contra um projeto Supabase real.

## Deviations from Assessment

- O callback aceita o formato oficial `token_hash` e também `token` somente quando acompanhado de `email`; o cliente Supabase exige o e-mail para validar um token OTP bruto.
- Não foi criada uma unidade frontend isolada: a verificação depende do navegador e do cliente Supabase; lint, TypeScript e build validam a rota. O teste real depende de e-mail e configuração externos.

## Follow-ups

- Atualizar o template **Confirm signup** no Supabase para usar `{{ .SiteURL }}/verify-email?token_hash={{ .TokenHash }}&type=email`.
- Adicionar `http://localhost:3000/verify-email` e a URL de produção à allowlist de Redirect URLs do Supabase.
- Confirmar o fluxo com um e-mail real em desenvolvimento e produção.
