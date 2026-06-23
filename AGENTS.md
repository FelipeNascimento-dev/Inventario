# AGENTS.md - Django C-Trends/Arancia

Este projeto usa Django e pode conter estrutura legada.

Regras principais:

- Preservar compatibilidade.
- Views devem ser enxutas quando possível.
- Regras complexas devem ir para services/helpers.
- Models devem representar dados e relacionamentos.
- Forms devem validar entrada.
- Templates não devem carregar regra de negócio pesada.
- Nunca assumir que `Group` sozinho identifica o cliente real.
- Quando depender de cliente/PA, usar UserDesignation e GAI.
- Não versionar secrets.
- Ao descobrir regra de negócio recorrente, registrar e propor nova rule em `.cursor/rules/2xx-business-<dominio>-auto.mdc`.
