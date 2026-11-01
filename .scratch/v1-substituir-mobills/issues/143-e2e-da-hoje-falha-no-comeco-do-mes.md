# Teste e2e da Hoje falha nos primeiros dias do mês

Type: task
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #335
Origem: CI vermelho do PR #332 ([ticket 132](132-edicao-em-lote-perde-o-dia-do-lancamento.md)) e da `main` em 01/11/2026

## O problema

`web/e2e/hoje.spec.ts:60` espera "94%" para a luz. Esse valor soma o boleto atrasado (`dia(-2)`) e a compra no cartão (`dia(-10)`). No começo do mês as duas datas caem no mês anterior e não entram na conta, então a tela mostra 85%. Em 01/11 o teste falhou no CI da `main` e no do PR #332. O teste depende do dia em que roda.

## Checklist

- [x] O teste passa em qualquer dia do mês: datas que caem no mês corrente, ou o relógio fixo
- [x] Rodar o teste com a data de hoje no dia 1, no dia 2 e no meio do mês

## Resolução

O teste calcula o percentual esperado da luz pelas datas que caem no mês: 85% da conta de luz, 7 pontos do boleto atrasado quando `dia(-2)` é deste mês e 2 pontos da compra no cartão quando a fatura fecha (`dia(-5)`) neste mês. A compra no cartão passou de R$ 25,00 para R$ 20,00, para todo percentual dar inteiro e não depender do arredondamento. Rodei o teste localmente no dia 1 (85%) e ele passou. O e2e usa o relógio real e esta sessão não tinha como adiantar a data, por isso não rodei nos dias 2 a 5 nem no meio do mês. No meio do mês o esperado volta aos 94% que o teste já conferia antes; nos dias 2 a 5 a conta usa a mesma regra.
