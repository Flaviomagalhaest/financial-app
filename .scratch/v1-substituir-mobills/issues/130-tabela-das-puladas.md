# Tabela de casos compartilhada para a conta das puladas

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #313
Origem: revisão (Standards) do [ticket 128](128-mostrar-as-puladas-na-tela.md)

## O problema

A [ADR 0018](../../../docs/adr/0018-aviso-de-planejamento-repete-regras-do-servidor-so-para-mostrar.md) manda que regra do servidor repetida no app tenha uma tabela de casos em `tabelas-de-teste/`, rodada pelo pytest e pelo Playwright. O ticket 128 repetiu no app `ocorrenciasPuladas`, `parcelasPuladas` e `maisMeses` (de `_gerar_um_lote` e `mais_meses`) e testou só pela tela, sem tabela.

## Checklist

- [ ] `tabelas-de-teste/puladas.json`: casos de recorrência (meses, semanas, dia 31, fim por `vezes` e por `ate`, início hoje/ontem) e de boleto/cartão, com `hoje` fixo
- [ ] pytest roda a tabela no servidor e `web/e2e/tabelas.spec.ts` no código do app
- [ ] Simplificar `avisoDasPuladas` (módulo certo, sem `?? null` nos usos)
