# Rules Django - Arancia/C-Trends

Esta pasta contém as rules ativas do Cursor para projetos Django da C-Trends, especialmente projetos com estrutura semelhante ao Arancia.

> As rules ativas são os arquivos `.mdc`. Este README é apenas documentação humana.

## Estrutura principal

```text
.cursor/rules/
├── 000-project-context-always.mdc
├── 010-django-architecture-always.mdc
├── 020-django-views-auto.mdc
├── 030-django-models-auto.mdc
├── 040-django-forms-auto.mdc
├── 050-templates-static-auto.mdc
├── 060-urls-routing-auto.mdc
├── 070-services-utils-auto.mdc
├── 080-auth-gai-userdesignation-always.mdc
├── 090-tests-auto.mdc
├── 100-security-settings-always.mdc
├── 110-docs-readme-auto.mdc
├── 115-reusable-core-abstractions-auto.mdc
├── 120-business-rules-discovery-manual.mdc
├── 201-business-identity-escopo-auto.mdc
├── 202-business-logistica-auto.mdc
├── 203-business-transportes-auto.mdc
├── 204-business-mural-auto.mdc
└── 205-business-backoffice-auto.mdc
```

## O que cada rule faz

| Rule | Finalidade |
| ---- | ---------- |
| `000` | Contexto global do projeto Django e fluxo recomendado. |
| `010` | Arquitetura geral: models, views, forms, services, utils e templates. |
| `020` | Boas práticas para views Django. |
| `030` | Regras para models e migrations. |
| `040` | Regras para forms. |
| `050` | Regras para templates, partials e static files. |
| `060` | Regras para urls e roteamento. |
| `070` | Regras para services e utils. |
| `080` | Regra obrigatória de User, Group, GAI e UserDesignation. |
| `090` | Testes Django. |
| `100` | Segurança, settings, secrets e permissões. |
| `110` | README, documentação e release notes. |
| `115` | Avaliação de classes reutilizáveis antes de criar novas classes. |
| `120` | Descoberta manual de regras de negócio para projetos existentes. |
| `201` | Identidade, GAI, elevação de escopo e permissões base (confirmado 2026-06-01). |
| `202` | Logística: last mile, estoque, reversa V1/V2, check-in, fulfillment. |
| `203` | Transportes: session COD_BASE, OS, viagens, CC_admin. |
| `204` | Mural: API externa, ger_mural, targeting, listagem por autor no gerenciamento. |
| `205` | Backoffice: importação Excel e cadastro via API BKO. |

## Regras de negócio específicas (série 2xx)

Regras confirmadas pelo time ficam em:

```text
.cursor/rules/2xx-business-<dominio>-auto.mdc
```

Ativas neste projeto (2026-06-01): `201`–`205`. Novos domínios seguem a numeração disponível (ex.: `206-business-...`).

## Business Rules auxiliares

A pasta `.cursor/business-rules/` não substitui as `.mdc`. Ela serve para registrar descobertas, perguntas e decisões antes de transformar uma regra em `.mdc` ativa.
