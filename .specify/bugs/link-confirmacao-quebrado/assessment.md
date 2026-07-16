# Bug Assessment: Link de confirmação de e-mail quebrado

- **Slug**: link-confirmacao-quebrado
- **Created**: 2026-07-15
- **Source**: pasted text
- **Verdict**: likely valid, needs reproduction
- **Severity**: high

## Report (verbatim or summarized)

> Ao tentar criar uma nova conta, o e-mail de confirmação enviado contém um link quebrado (exemplo: `http://localhost:3000undefined/verify-email?token=xyz`).

## Symptom

Após o cadastro, o Supabase envia um e-mail cujo link de confirmação contém o segmento literal `undefined` e aponta para `/verify-email`, impedindo a confirmação da conta. O esperado é um link válido para uma rota existente do frontend, capaz de concluir a confirmação.

## Reproduction

1. Abrir a tela de cadastro do frontend.
2. Criar uma nova conta com e-mail ainda não cadastrado.
3. Abrir o e-mail de confirmação e observar o destino do link.

O conteúdo real do template de e-mail e as configurações atuais do projeto Supabase ainda precisam ser confirmados.

## Suspected Code Paths

- `frontend/src/app/(auth)/register/page.tsx:31-61` — envia os dados do cadastro para `POST /accounts/register/` e apenas exibe a mensagem de sucesso; não define nem trata uma URL de confirmação.
- `backend/apps/accounts/views.py:15-45` — cria o perfil local após chamar o gateway do Supabase, sem fornecer redirect de confirmação.
- `backend/apps/accounts/supabase_gateway.py:18-21` — chama `auth.sign_up({"email": email, "password": password})`; o destino do e-mail fica dependente da configuração/template do Supabase.
- `frontend/src/app/(auth)/` — não há rota `verify-email`; as únicas rotas de callback encontradas são para recuperação de senha.
- `backend/.env.example:22-23` e `backend/config/settings/base.py:120-123` — documentam/configuram apenas o redirect de recuperação de senha, não o de confirmação de e-mail.

## Root Cause Hypothesis

**Confidence: medium.** O fluxo atual delega completamente a confirmação ao Supabase e não fornece `email_redirect_to` nem uma rota frontend correspondente. O `undefined` provavelmente vem de uma variável ausente no template de e-mail ou de uma URL de redirect não configurada no Supabase; a rota `/verify-email` também não existe neste repositório. A hipótese precisa ser confirmada inspecionando o template de confirmação e Auth → URL Configuration no projeto Supabase.

## Proposed Remediation

**Preferred**: definir explicitamente um redirect de confirmação válido no fluxo de `sign_up`, adicionar a rota frontend de confirmação compatível com o formato do link emitido pelo Supabase e configurar a mesma URL como permitida no Supabase. O destino deve ser dirigido por configuração de ambiente para separar desenvolvimento e produção. Também ajustar o template para usar a variável oficial de confirmação/redirect, sem concatenar valores potencialmente indefinidos.

**Files likely to change**:

- `backend/apps/accounts/supabase_gateway.py`
- `backend/config/settings/base.py`
- `backend/config/settings/prod.py`
- `frontend/src/app/(auth)/verify-email/page.tsx` ou rota de callback equivalente
- `backend/tests/contract/test_accounts_register.py`
- teste frontend da confirmação, se o callback exigir comportamento no cliente

**Tests to add or update**:

- Verificar que `sign_up` recebe o redirect de confirmação esperado.
- Verificar que a rota de confirmação existe e trata o callback válido e inválido.
- Verificar que nenhum link de confirmação pode conter `undefined`.
- Teste manual com um e-mail real em ambiente local e produção após atualizar o template/configuração do Supabase.

## Risks & Considerations

- A URL precisa estar na allowlist do Supabase Auth; caso contrário, o Supabase pode rejeitar o redirect ou continuar usando o Site URL.
- O formato do callback (`query`, `fragment` ou token/hash) depende da configuração e da versão do Supabase Auth; não deve ser presumido antes de inspecionar o link recebido.
- A criação do perfil local ocorre antes da confirmação; corrigir o link não resolve automaticamente perfis órfãos criados por tentativas anteriores.
- Alterar template e URL de produção é uma mudança de infraestrutura/configuração fora do código deste repositório.

## Open Questions

- [NEEDS CLARIFICATION: qual é o template atual de confirmação de e-mail no Supabase?]
- [NEEDS CLARIFICATION: qual é o valor atual de Auth → URL Configuration → Site URL e Redirect URLs?]
- [NEEDS CLARIFICATION: o link real usa parâmetros de query, fragmento/hash ou `{{ .ConfirmationURL }}`?]
- [NEEDS CLARIFICATION: qual deve ser a URL final em desenvolvimento e produção?]
