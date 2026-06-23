# Prompts Recomendados - Django Cursor Rules

## Analisar projeto existente

```text
Use a rule 120-business-rules-discovery-manual.mdc.

Analise todo o projeto Django atual sem alterar arquivos.
Quero que você identifique os apps principais, models, views, forms, templates, permissões e regras de negócio.
Separe regras confirmadas pelo código de regras inferidas.
Faça perguntas objetivas antes de propor novas rules.
```

## Criar nova tela/view

```text
Crie a nova tela [NOME] seguindo as rules do projeto Django.

Regras obrigatórias:
- verificar autenticação e permissão;
- considerar GAI/UserDesignation se a tela depender de cliente/PA;
- manter view enxuta;
- usar form quando houver entrada de dados;
- extrair regra complexa para service/helper;
- atualizar urls e template;
- explicar arquivos criados/alterados.
```

## Criar model

```text
Crie/ajuste o model [NOME] seguindo as rules de models Django.

Antes de alterar, avalie relacionamentos, migrations necessárias, __str__, verbose_name, choices e impacto em GAI/UserDesignation se houver relação com cliente/PA.
```

## Criar form

```text
Crie/ajuste o form [NOME] seguindo as rules de forms.

Mantenha validação de entrada no form e extraia regras complexas para service quando envolver múltiplos models, GAI ou UserDesignation.
```

## Criar service

```text
Crie um service para [REGRA/FLUXO].

A view deve apenas chamar o service.
O service deve concentrar a regra de negócio.
Não mova regra para model ou CRUD/helper sem justificativa.
```

## Criar classe reutilizável

```text
Preciso criar uma classe para [CAPACIDADE].

Use a rule 115-reusable-core-abstractions-auto.mdc e avalie se ela deve ficar em core/utils/common por ser reutilizável ou no app por ser específica de negócio.
```

## Criar rule de negócio após confirmação

```text
Com base nas regras confirmadas sobre [DOMÍNIO], crie uma nova rule em .cursor/rules/2xx-business-[dominio]-auto.mdc.

A rule deve ser objetiva, aplicável por globs e não pode depender apenas de suposições.
Atualize também .cursor/business-rules/decisions.md.
```
