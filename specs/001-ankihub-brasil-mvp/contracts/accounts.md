# Contract: Accounts (US-01, US-13)

Ver convenções gerais em `api-conventions.md`.

| Método | Rota | Auth | Descrição | Requisito |
|---|---|---|---|---|
| POST | `/api/v1/accounts/register/` | público | Cria conta (e-mail/senha via Supabase Auth) + perfil; recebe `name`, `target_career`, `target_board`, `consent_marketing_emails`, `consent_research_data` opcionais | FR-001, FR-004, FR-005 |
| POST | `/api/v1/accounts/password-reset/` | público | Dispara e-mail de recuperação (delegado ao Supabase Auth) | FR-003 |
| GET/PATCH | `/api/v1/accounts/me/` | usuário | Retorna o perfil ou atualiza o `name` opcional exibido na comunidade | FR-002, FR-047 |
| PATCH | `/api/v1/accounts/me/consents/` | usuário | Atualiza `consent_marketing_emails`/`consent_research_data`, efeito imediato | FR-045 |
| POST | `/api/v1/accounts/me/deletion-request/` | usuário | Agenda exclusão em 7 dias corridos | FR-046 |
| DELETE | `/api/v1/accounts/me/deletion-request/` | usuário | Cancela a exclusão agendada, dentro da carência | FR-046 |
| GET | `/api/v1/accounts/me/export/` | usuário | Retorna JSON com dados pessoais, sugestões e comentários do usuário | FR-047 |

**Erros de negócio notáveis**:
- `409` ao tentar cancelar exclusão já efetivada (prazo expirado).
- `403` em qualquer rota `me/*` se `is_suspended=true` (FR-049).
