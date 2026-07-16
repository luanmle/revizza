# Bug Verification: Link de confirmação de e-mail quebrado

- **Slug**: link-confirmacao-quebrado
- **Tested**: 2026-07-15
- **Assessment**: ./assessment.md
- **Fix**: ./fix.md
- **Result**: partial

## Summary

Os checks locais confirmam que o redirect é enviado explicitamente ao Supabase e que a rota `/verify-email` compila e é gerada pelo frontend. A reprodução real com envio de e-mail e projeto Supabase não foi executada, portanto o link final e a configuração externa continuam inconclusivos.

## Checks Performed

| Check | Command / Action | Result | Notes |
|-------|------------------|--------|-------|
| Reproduction (post-fix) | Criar conta e abrir o e-mail de confirmação em um projeto Supabase configurado | not-run | Depende de credenciais/configuração externa e de um e-mail real. |
| New / updated tests | `./.venv/bin/pytest -q tests/unit/test_supabase_gateway.py tests/contract/test_accounts_register.py` | pass | `6 passed`. |
| Regression suite | `npm run test -- --run` | pass | `14 passed` em 5 arquivos. |
| Lint / type-check | `npm run lint && npm run build` | pass | ESLint, TypeScript e build passaram; `/verify-email` foi gerada. |

## Output Excerpts

```text
6 passed in 1.78s
Test Files  5 passed (5)
Tests  14 passed (14)
✓ Compiled successfully
└ ○ /verify-email
```

## Residual Risks

- O template **Confirm signup** do Supabase ainda precisa usar `{{ .SiteURL }}/verify-email?token_hash={{ .TokenHash }}&type=email`.
- A URL local e a URL de produção precisam estar na allowlist de Redirect URLs do Supabase.
- O link quebrado pode continuar sendo gerado até que o template/configuração externa seja atualizado.

## Recommendation

Hold — a implementação local está validada, mas o bug só pode ser encerrado após um teste manual com e-mail real em ambiente configurado e confirmação de que o link não contém `undefined`.
