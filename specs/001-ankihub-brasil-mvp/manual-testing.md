# Guia de teste manual — AnkiHub Brasil MVP

Este guia descreve como subir o projeto localmente e validar manualmente o fluxo de recuperação
de senha concluído na T130, além dos checks de qualidade da T142. Ele usa o Supabase hospedado e
não exige alteração no código-fonte.

## 1. Pré-requisitos

- Python 3.12 com o ambiente virtual do backend instalado.
- Node.js 22 ou superior com as dependências do frontend instaladas.
- Um projeto Supabase de desenvolvimento com autenticação por e-mail habilitada.
- Uma conta de teste existente no Supabase e acesso à caixa de entrada desse e-mail.
- Backend e frontend configurados conforme os arquivos de exemplo:
  - `backend/.env.example`
  - `frontend/.env.local.example`

> Use uma conta exclusiva para testes. Não compartilhe links de recuperação, fragmentos de URL,
> access tokens nem a chave secreta do backend.

## 2. Configurar o Supabase

No Supabase Dashboard, abra **Authentication → URL Configuration** e configure:

```text
Site URL: http://localhost:3000
Redirect URL: http://localhost:3000/password-reset/callback
```

Confirme também que:

1. O provedor **Email** está habilitado em **Authentication → Providers**.
2. A URL de callback está cadastrada exatamente como acima, sem trocar porta ou caminho.
3. O template de recuperação usa o fluxo implícito padrão do Supabase. Um template personalizado
   com `token_hash`/PKCE exige outro tipo de callback e não pertence a este teste.

## 3. Configurar o backend

Abra o primeiro terminal:

```bash
cd backend
source .venv/bin/activate

export SUPABASE_URL='https://SEU-PROJETO.supabase.co'
export SUPABASE_SERVICE_ROLE_KEY='sb_secret_...'
export PASSWORD_RESET_REDIRECT_URL='http://localhost:3000/password-reset/callback'

python manage.py migrate
python manage.py runserver
```

Resultado esperado:

```text
Starting development server at http://127.0.0.1:8000/
```

> O backend atual lê essas configurações de variáveis de ambiente. Copiar `.env.example` para
> `.env` não carrega automaticamente os valores no processo do Django.

## 4. Configurar e iniciar o frontend

Em `frontend/.env.local`, use:

```env
NEXT_PUBLIC_SUPABASE_URL=https://SEU-PROJETO.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_...
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Nunca coloque `sb_secret_...` em uma variável `NEXT_PUBLIC_*`.

Abra o segundo terminal:

```bash
cd frontend
npm run dev
```

Resultado esperado:

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8000
```

## 5. Preparar a conta de teste

Se já houver uma conta confirmada cujo e-mail você consegue acessar, pule esta seção.

1. Abra `http://localhost:3000/register`.
2. Cadastre um e-mail de teste e uma senha conhecida.
3. Abra o e-mail de confirmação enviado pelo Supabase.
4. Confirme a conta.
5. Entre em `http://localhost:3000/login` para validar a senha atual.
6. Saia da conta ou abra uma janela anônima antes de iniciar a recuperação.

## 6. Fluxo principal de recuperação de senha

### Passo 1 — Solicitar o link

1. Abra `http://localhost:3000/password-reset`.
2. Informe o e-mail da conta de teste.
3. Selecione **Enviar link de recuperação**.

Resultado esperado:

```text
Se o e-mail existir, você receberá um link de redefinição.
```

A mensagem deve ser genérica para não revelar se uma conta existe.

### Passo 2 — Abrir o e-mail

1. Abra a caixa de entrada da conta de teste.
2. Verifique também a pasta de spam.
3. Abra o e-mail de recuperação.
4. Selecione o link somente uma vez.

Resultado esperado:

- O navegador abre `http://localhost:3000/password-reset/callback`.
- A página mostra o título **Criar nova senha**.
- Os campos **Nova senha** e **Confirmar nova senha** ficam disponíveis.

O Supabase usa um link de uso único. Não copie nem compartilhe o fragmento contendo o token.

### Passo 3 — Definir a nova senha

1. Preencha **Nova senha** com pelo menos 8 caracteres.
2. Repita o mesmo valor em **Confirmar nova senha**.
3. Selecione **Alterar senha**.

Resultado esperado:

```text
Senha alterada. Você já pode usar a nova senha.
```

### Passo 4 — Validar as credenciais

1. Volte para `http://localhost:3000/login`.
2. Entre usando o e-mail de teste e a senha nova.
3. Saia da conta.
4. Tente entrar com a senha antiga.

Resultados esperados:

- A senha nova autentica com sucesso.
- A senha antiga é recusada.

## 7. Cenários negativos

Execute cada cenário separadamente.

| Cenário              | Procedimento                                       | Resultado esperado                                                       |
| -------------------- | -------------------------------------------------- | ------------------------------------------------------------------------ |
| Senhas diferentes    | Informar valores diferentes nos dois campos        | Mensagem **As senhas não coincidem.**                                    |
| Senha curta          | Informar menos de 8 caracteres                     | O navegador impede o envio do formulário                                 |
| Callback sem token   | Abrir `/password-reset/callback` diretamente       | Mensagem de link inválido ou expirado                                    |
| Link reutilizado     | Abrir novamente um link já consumido               | Link recusado como inválido ou expirado                                  |
| Link expirado        | Usar um link após sua validade                     | Link recusado e opção para solicitar outro                               |
| E-mail inexistente   | Solicitar recuperação para endereço não cadastrado | Mesma resposta genérica do fluxo válido; nenhum dado da conta é revelado |
| Backend indisponível | Parar o Django e solicitar um link                 | Mensagem **Não foi possível enviar o link. Tente novamente.**            |
| Solicitação repetida | Solicitar outro link imediatamente                 | O Supabase pode aplicar o limite padrão de aproximadamente 60 segundos   |

## 8. Smoke test de regressão

Depois de alterar a senha:

1. Entre com a senha nova.
2. Abra o catálogo em `/decks`.
3. Abra um deck.
4. Confirme que a sessão permanece válida durante a navegação.
5. Saia da conta.
6. Confirme que uma rota protegida volta a exigir autenticação.

## 9. Checks de qualidade da T142

Estes comandos não alteram o código-fonte; apenas verificam formatação, lint e build.

Na raiz do repositório:

```bash
backend/.venv/bin/ruff check backend addon
backend/.venv/bin/black --check backend addon
```

No frontend:

```bash
cd frontend
npm run lint
npx prettier --check .
npm test
npm run build
```

Para o teste E2E automatizado do mesmo fluxo:

```bash
cd frontend
npx playwright install chromium  # necessário apenas na primeira execução
npm run test:e2e
```

Todos os comandos devem terminar com código de saída `0`.

## 10. Solução de problemas

### O e-mail não chegou

1. Aguarde pelo menos 60 segundos antes de solicitar outro link.
2. Verifique spam e promoções.
3. Confirme que o endereço pertence a uma conta existente.
4. Consulte os logs de Auth no Supabase Dashboard.
5. Se houver SMTP personalizado, desative rastreamento de links durante o diagnóstico.

### O callback informa link inválido

1. Confirme que frontend e backend continuam rodando.
2. Confira a URL permitida no Supabase Dashboard.
3. Solicite um link novo e abra apenas o mais recente.
4. Verifique se um antivírus ou scanner de e-mail consumiu o link antes do navegador.
5. Confirme que o template de recuperação não foi convertido para `token_hash`/PKCE.

### A solicitação falha imediatamente

1. Confira `NEXT_PUBLIC_API_URL` no frontend.
2. Confirme que o backend responde em `http://localhost:8000`.
3. Confirme `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e
   `PASSWORD_RESET_REDIRECT_URL` no processo do Django.
4. Verifique o console do backend e os logs de Auth do Supabase.

## 11. Checklist final

- [ ] Backend iniciado em `localhost:8000`.
- [ ] Frontend iniciado em `localhost:3000`.
- [ ] Redirect URL cadastrada no Supabase.
- [ ] Conta de teste confirmada e acessível.
- [ ] E-mail de recuperação recebido.
- [ ] Callback abriu o formulário de senha nova.
- [ ] Senha nova foi aceita.
- [ ] Login com senha nova funcionou.
- [ ] Login com senha antiga foi recusado.
- [ ] Link reutilizado foi recusado.
- [ ] E-mail inexistente não revelou a existência da conta.
- [ ] Cenários negativos produziram mensagens adequadas.
- [ ] Ruff, Black, ESLint e Prettier passaram.
- [ ] Testes e build do frontend passaram.

## Referências

- [Supabase — Password-based Auth](https://supabase.com/docs/guides/auth/passwords)
- [Supabase JS — resetPasswordForEmail](https://supabase.com/docs/reference/javascript/auth-resetpasswordforemail)
- [Supabase — Redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)
- [Supabase — Production Checklist](https://supabase.com/docs/guides/deployment/going-into-prod)
