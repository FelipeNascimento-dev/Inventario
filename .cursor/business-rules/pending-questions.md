# Perguntas Pendentes

Registro de dúvidas antes de transformar regras em `.cursor/rules/2xx-business-*-auto.mdc`.

| Data | Módulo | Pergunta | Status |
| ---- | ------ | -------- | ------ |
| 2026-06-01 | Identidade | Todo usuário operacional deve ter `UserDesignation.informacao_adicional` preenchido, ou existem grupos válidos sem GAI? | **Confirmado:** sem GAI = inválido |
| 2026-06-01 | Identidade | `sales_channel == 'all'` no GAI é equivalente a `gestao_total`, ou são escopos diferentes? Qual usar em código novo? | **Confirmado:** ambas = ver tudo; não mudar uso existente |
| 2026-06-01 | Identidade | Usuário pode pertencer a vários grupos `arancia_*` mantendo um único GAI? Como resolver conflito de skill vs escopo? | Pendente |
| 2026-06-01 | Identidade | Existe papel “super” (`ti_interno`, superuser) que bypassa filtros GAI em todas as telas, ou só as permissões listadas (`gestao_total`, `gerente_estoque`, `CC_admin`, etc.)? | Pendente |
| 2026-06-01 | Logística | Reversa V1 (`/reverse/`) ou V2 (`/reversa/`) é o fluxo oficial? O outro está em depreciação? | **Confirmado:** ambos em produção; deixar como está |
| 2026-06-01 | Logística | Modelos locais `Romaneio` / `RomaneioReverse` ainda são usados ou são legado totalmente substituído pela Stock API? | Pendente |
| 2026-06-01 | Logística | Permissões `checkout_principal`, `estoque`, `products_management`, `receber_checkin` — ainda vigentes (menu/template) ou podem ser ignoradas? | Pendente |
| 2026-06-01 | Logística | `PontoAtendimentoInfo.limite` e `liberado` devem ser aplicados no check-in ou são obsoletos? | Pendente |
| 2026-06-01 | Transportes | `CC_gerencial`, `controle_chamados`, `transp_menu` — devem ser enforced em views ou são apenas legado? | Pendente |
| 2026-06-01 | Transportes | Escopo de transportes: session `COD_BASE` substitui GAI ou complementa? Qual prevalece? | Pendente |
| 2026-06-01 | Backoffice | Permissão `backoffice.BKO` tem uso previsto ou só `Importar` é relevante? | Pendente |
| 2026-06-01 | Mural | Gerenciamento deve listar só itens do autor ou gerentes veem mural de toda a organização? | **Confirmado:** só itens do autor (`by-created-by`); manter como está |
| 2026-06-01 | Mural | Devemos alinhar `view_mural.py` para exigir `ger_mural` no servidor (como `gerenciamento_mural.py`)? | **Confirmado:** não; manter como está |
| 2026-06-01 | Mural | Targeting no create: operador com `ger_mural` pode mirar qualquer GAI Arancia ou há limite por designação? | Pendente |
| 2026-06-01 | Geral | Prioridade para criar rules ativas: qual domínio formalizar primeiro — identidade/GAI, logística, transportes, mural ou backoffice? | **Confirmado:** criar todas (`201`–`205`) |
