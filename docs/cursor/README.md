# Guia de Aplicação - Cursor Rules Django

Este guia explica como aplicar as rules em projetos Django já existentes.

## Aplicando em um projeto existente

1. Copie `.cursor/`, `AGENTS.md`, `.cursorrules` e `docs/cursor/` para a raiz do projeto.
2. Abra o projeto no Cursor pela raiz.
3. Execute primeiro uma análise sem alterar arquivos.
4. Use a rule manual 120 para descobrir regras de negócio.
5. Confirme regras com o time.
6. Crie rules específicas em `.cursor/rules/2xx-business-<dominio>-auto.mdc`.

## Fluxo para projeto legado

```text
Analisar -> Perguntar -> Confirmar -> Criar rule -> Implementar -> Documentar
```

## Sobre GAI e UserDesignation

Nunca assumir que `Group` sozinho identifica o cliente real do usuário. Para funcionalidades com escopo de cliente/PA, verificar UserDesignation e GAI.

## Quando criar nova rule de negócio

Crie nova rule quando uma regra:

- for recorrente;
- impactar segurança/permissão;
- afetar criação de views/endpoints/telas;
- puder ser descumprida facilmente por IA;
- representar decisão oficial do time.

Não crie rule para detalhe pequeno ou temporário.
