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
- Deploy produção: Swarm `inventario_gtn` — ver `.cursor/rules/130-deploy-swarm-inventario-gtn-always.mdc` e `docs/contexto_infra_swarm_cursor.md`. Nova variável de env exige orientação explícita para `/opt/envs/inventario-gtn.env`.
- Ao descobrir regra de negócio recorrente, registrar e propor nova rule em `.cursor/rules/2xx-business-<dominio>-auto.mdc`.
