# Contract: Content Reports & Admin Review (US-14)

Ver convenções gerais em `api-conventions.md`. A criação de uma denúncia acontece via
`POST /comments/{id}/reports/` ou `POST /suggestion-comments/{id}/reports/` (ver `notes.md` e
`suggestions.md`) — este contrato cobre apenas a fila de revisão, que no MVP roda inteiramente pelo
Django admin nativo (PRD §2.2/US-14), sem tela dedicada no frontend.

| Método | Rota | Auth | Descrição | Requisito |
|---|---|---|---|---|
| — | Django Admin: `Report` | administrador da plataforma | Lista denúncias `pending`, permite remover o conteúdo denunciado e, se necessário, suspender (`is_suspended=true`) o autor do conteúdo | FR-049 |

Ao marcar uma denúncia como `reviewed` com remoção de conteúdo, o backend dispara e-mail
transacional síncrono ao autor do conteúdo removido informando o motivo (ver research.md §6).

| Efeito colateral | Descrição | Requisito |
|---|---|---|
| E-mail de notificação | Enviado ao autor do conteúdo removido, com o motivo da remoção | FR-050 |
| Autenticação obrigatória | Toda denúncia é vinculada a um denunciante autenticado — sem denúncia anônima | FR-051 |
