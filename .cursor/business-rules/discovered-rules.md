# Regras de Negócio Descobertas

Análise executada em 2026-06-01 via rule `120-business-rules-discovery-manual.mdc`.

Apps analisados: `logistica`, `transportes`, `backoffice`, `mural`.

---

## Confirmadas pelo código

### Identidade, GAI e UserDesignation

1. **GAI (`GroupAditionalInformation`)** representa a unidade operacional real (PA, CD, cliente, transportadora): `cod_iata`, `sales_channel`, `cod_center`, `deposito`, `nome`, CNPJ, endereço. Cada GAI está ligado a um Django `Group` pelo FK `group`.
   - Evidência: `logistica/models.py` (classe `GroupAditionalInformation`).

2. **UserDesignation** é `OneToOne` com `User` (`related_name='designacao'`) e aponta para um único GAI via `informacao_adicional`.
   - Evidência: `logistica/models.py` (classe `UserDesignation`).

3. **Acesso padrão:** `request.user.designacao.informacao_adicional` (ou `_id`) define escopo operacional em romaneio, reversa, estoque, remessa, mural, transportes.
   - Evidência: dezenas de views em `logistica/views/`, `transportes/views/`, `mural/views/`.

4. **Criação de usuário exige coerência grupo + GAI:** o GAI selecionado deve pertencer ao mesmo Django `Group` da skill escolhida.
   - Evidência: `logistica/forms/forms_create_user.py` (validação `gai.group_id != grupo.id`).

5. **Usuários internos Arancia** usam prefixo `ARC` no username; skills usam grupos `name__startswith="arancia_"`.
   - Evidência: `forms_create_user.py`, `view_gestao_usuarios.py`, `gerenciamento_mural.py`.

6. **Não existe helper centralizado** (`get_user_designation`, service de escopo). Regras repetidas view a view.
   - Evidência: busca em todo o repositório — ausência de função compartilhada.

### Permissões base

7. **`logistica.acesso_arancia`** é o gate principal da plataforma; quase todas as views protegidas exigem login + essa permissão.
   - Evidência: decorators em `logistica/`, `transportes/`, `mural/`.

8. **Permissões customizadas** vivem em modelos dummy:
   - `logistica.PermissaoUsuarioDummy` — `gestao_total`, `pode_gerenciar_filiais`, `gerente_estoque`, `lastmile_b2c`, `checkin_principal`, `entrada_flfm`, `reverse`, `full_checkin`, etc.
   - `transportes.PersonalPermissions` — `CC_admin`, `CC_gerencial`, `controle_campo`, `ver_transportes`, etc.
   - `backoffice.PersonalPermissions` — `Importar`, `BKO`.
   - `mural.MuralPermissions` — `ger_mural`.
   - Evidência: `models.py` de cada app.

### Elevação de escopo (ver todos os GAIs / PAs)

9. **`sales_channel == 'all'`** no GAI do usuário implica escopo ampliado: `location_id = 0` ou listas de todos os PAs em reversa, checkout, recebimento remessa, romaneio V2.
   - Evidência: `views_reverse/view_criar_reversa.py`, `viewsV2/view_lista_romaneios.py`, `view_recebimento_remessa.py`, `view_checkout_reverse.py`.

10. **`logistica.gestao_total`** desbloqueia escolha de origem PA/CD em check-in, checkout reverse, gestão de usuários/skills e CRUD motorista/veículo em transportes.
    - Evidência: `view_checkin_registrar.py`, `view_checkout_reverse.py`, `view_gestao_usuarios.py`, `transportes/.../view_criar_veiculo.py`.

11. **`logistica.pode_gerenciar_filiais`** permite ver todos os `sales_channel` distintos da tabela GAI em consulta de pedidos.
    - Evidência: `view_consulta_pedidos.py` (`get_user_sales_channel`).

12. **`logistica.gerente_estoque`** vê todos os GAIs com `group__name__icontains="arancia_pa"`; demais usuários só o próprio GAI.
    - Evidência: `view_gerenciamento_estoque.py`.

13. **`transportes.CC_admin`** vê todas as bases PA em OS pendentes; demais ficam em `PA_{cod_iata}` da designação.
    - Evidência: `view_consulta_os_pend.py` (`usuario_pode_ver_todas_bases`, `get_base_usuario`).

14. **Membros do grupo Django `arancia_PA`** em lista de viagens não podem filtrar outro PA — `pa_selecionada` é forçado ao GAI da designação.
    - Evidência: `view_lista_viagens.py`.

### Fluxos por módulo

#### Logística — last mile / estoque / reversa

15. **Romaneio/reversa operacional usa APIs externas** (`STOCK_API_URL`, `API_URL`), não as tabelas locais `Romaneio`/`RomaneioReverse`.
    - Evidência: `views_reverse/`, `viewsV2/`, `views_recebimento_estoque/`.

16. **`logistica.lastmile_b2c`** + `acesso_arancia` protegem estoque, reversa, remessa, receber em estoque.
    - Evidência: decorators em `views_reverse/`, `views_lastmile_consultas/`, `views_recebimento_estoque/`.

17. **`logistica.reverse`** controla destinos de reversa (CDs Flex) no formulário.
    - Evidência: `forms_reverse/forms_criar_reversa.py`.

18. **Check-in:** cliente `cielo` + vetor `OUT` redireciona para checkout reverse; demais IN → check-in, OUT → checkout reverse.
    - Evidência: `view_checkin_iniciar.py`.

19. **Check-in exige `checkin_principal`**; produto visível para superuser, `full_checkin` ou GAI nome `"ctb tatuapé 81"`.
    - Evidência: `view_checkin_iniciar.py`, `forms_checkin_registrar.py`.

20. **Fulfillment SAP exige `entrada_flfm`.**
    - Evidência: `view_fullfilment/view_recebimentos.py`, `view_consulta_id.py`.

21. **Fluxo entrega (reserva/saída)** usa `deposito` e `cod_center` do GAI da designação.
    - Evidência: `view_reserva_equip.py`, `view_saida_campo.py`.

#### Transportes

22. **Controle de campo exige session `COD_BASE` / `PROJETO` / `PROFILE`** — escopo por sessão, não por GAI diretamente.
    - Evidência: `View_session.py`, `dashboard_view.py`.

23. **Bases PA para chamados** vêm de todos os GAIs do grupo `arancia_PA`.
    - Evidência: `get_bases_from_arancia_pa()` em `view_consulta_os_pend.py`, `view_lista_tecnicos.py`.

24. **Transportes operacional exige `ver_transportes`** + `acesso_arancia`.
    - Evidência: `view_consulta_os_transp.py`, `view_lista_viagens.py`.

#### Backoffice

25. **Importação e cadastro de equipamentos exigem `backoffice.Importar`.**
    - Evidência: `importar_view.py`, `cadastro_equipamento_view.py`, `baixar_ignorados_view.py`.

26. **Backoffice delega persistência à API `API_BASE_BKO`.**
    - Evidência: views em `backoffice/views/`.

#### Mural

27. **Conteúdo do mural vive na API externa (`MURAL_API_URL`); Django só guarda permissão `mural.ger_mural`.**
    - Evidência: `mural/models.py`, chamadas HTTP em `view_mural.py`, `gerenciamento_mural.py`.

28. **Feed do consumidor** lista itens via `GET /v1/items/by-user/` com `user_id` + `gai_id` da designação.
    - Evidência: `mural/views/view_mural.py`.

29. **Gerenciamento** lista itens criados pelo usuário (`by-created-by/?created_by_id=`) e exige `mural.ger_mural` para create/edit/disable.
    - Evidência: `mural/views/gerenciamento_mural.py`. **Confirmado pelo time: manter assim.**

30. **Item crítico** tem duração máxima de 7 dias — validado no Django antes de chamar API.
    - Evidência: `validate_critical_duration` em ambas as views mural.

31. **Tipos de item:** `announcement`, `notice`, `script`, `manual`. Severidades: `informational`, `moderate`, `important`, `critical`. Targeting: `all`, `users`, `groups`, `gais`.
    - Evidência: templates e views mural.

32. **Diferença intencional de permissão no mural:** `view_mural.py` não verifica `ger_mural` no servidor para create/edit/disable (só UI); `gerenciamento_mural.py` verifica no servidor. **Decisão do time: manter assim.**
    - Evidência: comparar POST handlers nas duas views; `decisions.md`.

### Grupos Django recorrentes

| `Group.name` | Papel |
|--------------|-------|
| `arancia_PA` | Ponto de atendimento |
| `arancia_CD` | Centro de distribuição |
| `arancia_CUSTOMER` | Cliente/localidade (transportes) |
| `arancia_TRANSPORT` | Transportadora |

---

## Confirmadas pelo time (2026-06-01)

33. **Usuário sem GAI é inválido** — todo usuário operacional deve ter `UserDesignation.informacao_adicional` preenchido.
    - Decisão registrada em `decisions.md`.

34. **`sales_channel == 'all'` e `gestao_total`** são ambas flags de escopo ampliado (“ver tudo”), usadas em telas diferentes ao longo do tempo. **Não unificar** — respeitar o padrão de cada view existente.
    - Decisão registrada em `decisions.md`.

35. **Reversa V1 e V2 coexistem** — partes de cada versão estão em produção; não depreciar sem solicitação explícita.
    - Decisão registrada em `decisions.md`.

36. **Gerenciamento mural lista itens do autor** — `by-created-by/?created_by_id=` em `gerenciamento_mural.py`. Comportamento **correto**; não alterar.
    - Decisão registrada em `decisions.md`.

---

## Inferidas e pendentes de confirmação

1. **Usuário com múltiplos grupos `arancia_*` e um único GAI** — UI de edição permite vários grupos; comportamento esperado?

2. **`ti_interno`, `CC_gerencial`, `controle_chamados`, `BKO`** — permissões definidas nos models mas não encontradas em `permission_required` nas views (menu-only? legado?).

3. **`checkout_principal`, `products_management`, `estoque`, `receber_checkin`, `desinstalacao`** — declaradas em logistica mas sem enforcement em views.

4. **`PontoAtendimentoInfo.limite` / `liberado`** — configurado no admin; não referenciado em check-in.

5. **Modelos locais `Romaneio`/`RomaneioReverse`** — legado ou ainda escritos em algum fluxo?

6. **Mural:** API externa é autoridade final para visibilidade, expiração e leituras; Django não revalida targeting no create.

7. **`lista_viagens`** usa grupo Django `arancia_PA` além de designação — diverge da regra “Group sozinho não identifica cliente”.

8. **`view_reads` (quem leu)** pode ser chamado sem `ger_mural` no servidor — vazamento se API não autorizar.

9. **Check-in:** lista de clientes vem de `STOCK_API_URL/v1/clients/`, não filtrada por GAI no Django.

10. **`cod_base = "CTBSEQ"`** hardcoded em partes de `view_consulta_os_pend.py` — específico de ambiente?

