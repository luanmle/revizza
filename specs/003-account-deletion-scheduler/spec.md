# Feature Specification: Scheduler de Deleção de Contas (LGPD)

**Feature Branch**: `003-account-deletion-scheduler`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Scheduler de deleção de contas (LGPD) — a lógica de exclusão após a carência de 7 dias existe e é testada, mas nada a executa periodicamente em produção; contas marcadas para exclusão nunca são de fato apagadas."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Exclusão automática após a carência (Priority: P1)

Como usuário que solicitou a exclusão da própria conta, espero que meus dados sejam efetivamente apagados assim que os 7 dias de carência (LGPD) terminarem, sem que ninguém precise executar nada manualmente.

**Why this priority**: É a obrigação legal (LGPD) que motiva a feature inteira. Sem execução automática, a carência de 7 dias é apenas um valor no banco — a exclusão nunca acontece na prática, o que é uma não-conformidade ativa em produção.

**Independent Test**: Marcar uma conta de teste para exclusão com `deletion_requested_at` há mais de 7 dias, aguardar o próximo ciclo de execução automática (sem intervenção humana) e confirmar que a conta e os dados associados foram removidos.

**Acceptance Scenarios**:

1. **Given** uma conta com `deletion_requested_at` há mais de 7 dias, **When** o ciclo periódico seguinte roda, **Then** a conta é excluída automaticamente, sem ação manual de qualquer pessoa.
2. **Given** uma conta com `deletion_requested_at` há menos de 7 dias, **When** o ciclo periódico roda, **Then** a conta permanece intacta.
3. **Given** nenhuma conta elegível no momento do ciclo, **When** o ciclo roda, **Then** nada é alterado e a execução é registrada normalmente (zero exclusões).

---

### User Story 2 - Isolamento de falhas entre contas (Priority: P2)

Como responsável por operar a plataforma, quero que a falha ao excluir uma conta (ex.: erro temporário no provedor de autenticação) não impeça a exclusão das demais contas elegíveis no mesmo ciclo, e que essa conta falha seja automaticamente retentada no próximo ciclo.

**Why this priority**: Sem isolamento, uma única falha externa pode travar a exclusão de todas as outras contas elegíveis, ampliando o descumprimento da obrigação legal a mais usuários do que o necessário.

**Independent Test**: Simular falha na exclusão de uma conta entre várias elegíveis no mesmo ciclo e confirmar que as demais são excluídas normalmente, e que a conta com falha continua elegível e é excluída num ciclo posterior sem duplicidade.

**Acceptance Scenarios**:

1. **Given** múltiplas contas elegíveis no mesmo ciclo, **When** a exclusão de uma delas falha, **Then** as demais contas elegíveis são excluídas normalmente no mesmo ciclo.
2. **Given** uma conta cuja exclusão falhou em um ciclo, **When** o próximo ciclo roda, **Then** essa conta é retentada automaticamente até ser excluída com sucesso.

---

### User Story 3 - Registro auditável de cada execução (Priority: P3)

Como responsável por compliance, quero um registro auditável de cada execução do ciclo de exclusão (quantas contas foram excluídas e quando), para poder comprovar o cumprimento da obrigação LGPD quando solicitado.

**Why this priority**: Importante para auditoria e comprovação de conformidade, mas não impede a exclusão em si acontecer — por isso vem depois da execução automática e da resiliência a falhas.

**Independent Test**: Rodar um ciclo com contas elegíveis conhecidas e verificar que existe um registro consultável com o número de contas excluídas e o horário da execução.

**Acceptance Scenarios**:

1. **Given** um ciclo que exclui N contas, **When** o ciclo termina, **Then** existe um registro auditável com o valor de N e o timestamp da execução.
2. **Given** um ciclo que falha ao excluir alguma conta, **When** o ciclo termina, **Then** o registro auditável distingue exclusões bem-sucedidas de falhas.

---

### Edge Cases

- O que acontece se o ciclo periódico rodar mais de uma vez para a mesma janela de tempo (sobreposição/reexecução)? Nenhuma conta já excluída pode ser processada de novo nem gerar erro; contas ainda não vencidas não devem ser afetadas (idempotência).
- O que acontece se o provedor de autenticação externo (Supabase Auth) ficar indisponível por vários ciclos seguidos? As contas elegíveis continuam acumulando e sendo retentadas a cada ciclo, sem perda de dados e sem exclusão parcial (perfil apagado localmente mas mantido no provedor externo, ou vice-versa).
- O que acontece se uma conta acumular múltiplas tentativas de exclusão falhas? Ela continua elegível indefinidamente até ter sucesso; não há descarte automático da obrigação de exclusão.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE executar a rotina de exclusão de contas expiradas automaticamente, pelo menos uma vez a cada 24 horas, em produção, sem exigir disparo manual de qualquer pessoa.
- **FR-002**: O sistema DEVE excluir apenas contas cuja carência de 7 dias (`deletion_requested_at`) já tenha vencido no momento da execução.
- **FR-003**: O sistema NÃO DEVE alterar contas dentro do período de carência.
- **FR-004**: O sistema DEVE ser seguro para rodar mais de uma vez no mesmo dia ou em janelas sobrepostas, sem duplicar exclusões nem gerar erro sobre contas já excluídas (idempotência).
- **FR-005**: Uma falha ao excluir uma conta específica (ex.: erro no provedor de autenticação externo) NÃO DEVE impedir a exclusão das demais contas elegíveis no mesmo ciclo.
- **FR-006**: Uma conta cuja exclusão falhe em um ciclo DEVE continuar elegível e ser automaticamente retentada nos ciclos seguintes, sem intervenção manual.
- **FR-007**: Cada execução do ciclo DEVE gerar um registro auditável contendo, no mínimo, o número de contas excluídas com sucesso e o timestamp da execução.
- **FR-008**: O registro auditável DEVE permitir distinguir exclusões bem-sucedidas de tentativas que falharam.

### Key Entities

- **Conta (User)**: usuário da plataforma com campo `deletion_requested_at` indicando quando a exclusão foi solicitada; alvo da exclusão quando a carência vence.
- **Execução do ciclo (Run)**: uma rodada periódica da rotina de exclusão; possui timestamp, quantidade de contas excluídas e quantidade de falhas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das contas com carência vencida são excluídas em até 24 horas após o vencimento, sem qualquer ação manual, comprovado em produção ou ambiente equivalente.
- **SC-002**: 0% das contas dentro da carência são afetadas por qualquer execução do ciclo.
- **SC-003**: Uma falha isolada na exclusão de uma conta não atrasa a exclusão de nenhuma outra conta elegível no mesmo ciclo.
- **SC-004**: 100% das execuções do ciclo produzem um registro auditável consultável, com contagem de exclusões e timestamp.

## Assumptions

- A lógica de negócio de exclusão (`delete_expired_accounts`) e a carência de 7 dias já estão corretas e não fazem parte desta feature — o escopo aqui é garantir que essa lógica seja disparada periodicamente e de forma resiliente/auditável.
- "Automaticamente, sem intervenção manual" significa um agendamento recorrente operado pela própria infraestrutura de produção (não depende de alguém lembrar de rodar um comando).
- Uma cadência diária atende ao requisito legal de 7 dias de carência (folga suficiente mesmo com atraso de algumas horas entre execuções).
- O mecanismo concreto de agendamento (ex.: add-on de scheduler, processo dedicado, cron externo) é uma decisão de implementação, a ser resolvida na fase de planejamento, não nesta especificação.
