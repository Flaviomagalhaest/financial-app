# Teste e2e da Hoje falha nos primeiros dias do mês

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #335
Origem: CI vermelho do PR #332 ([ticket 132](132-edicao-em-lote-perde-o-dia-do-lancamento.md)) e da `main` em 01/11/2026

## O problema

`web/e2e/hoje.spec.ts:60` espera "94%" para a luz. Esse valor soma o boleto atrasado (`dia(-2)`) e a compra no cartão (`dia(-10)`). No começo do mês as duas datas caem no mês anterior e não entram na conta, então a tela mostra 85%. Em 01/11 o teste falhou no CI da `main` e no do PR #332. O teste depende do dia em que roda.

## Checklist

- [ ] O teste passa em qualquer dia do mês: datas que caem no mês corrente, ou o relógio fixo
- [ ] Rodar o teste com a data de hoje no dia 1, no dia 2 e no meio do mês
