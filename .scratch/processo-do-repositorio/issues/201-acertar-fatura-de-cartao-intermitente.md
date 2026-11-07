# Acertar fatura de cartão falha de vez em quando no teste de navegador

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`, `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #518
Origem: [ticket 119](../../v1-substituir-mobills/issues/119-busca-medir-no-dsql-e-uma-passada.md): CI do PR #511 (job `verificar`, commit 823f41b, run 42415189815). O PR só mudou `backend/app/busca.py`, `backend/medir_busca.py` e o ticket 119; o mesmo job passou nos dois commits anteriores.

## O problema

`web/e2e/cartoes-cadastro.spec.ts:78` ("acerta o fechamento e o vencimento de uma fatura existente e de outra escolhida pelo mês, com o aviso de redistribuição") falhou na linha 103, `form.getByLabel("Fatura").selectOption(...)`, com "strict mode violation": o rótulo "Fatura" casou com dois elementos, o `select` "Fatura" e o `input type=month` "Mês da fatura" (o `getByLabel` sem `exact` casa por trecho). Os 329 outros testes passaram.

Causa provável: o `FormularioDeFatura` (`web/src/contas-e-categorias/SecaoDeCartoes.tsx`) abre com a lista de faturas guardada, que pode ser de antes da compra do teste e vir vazia; sem fatura, ele escolhe "Outro mês…" e mostra o campo "Mês da fatura". Quando a lista nova chega, ele troca para a fatura atual. Na janela entre as duas, os dois campos existem juntos e o seletor do teste, que não é exato, é ambíguo.

## Checklist

- [ ] Reproduzir (o teste repetido com `--repeat-each`, ou com a CPU saturada como no ticket 109)
- [ ] Confirmar a causa e corrigir sem desligar o teste: o seletor exato (`getByLabel("Fatura", { exact: true })`) e a espera pela fatura nascida (`toHaveValue` do `select`) antes de escolher; se a janela com "Outro mês…" selecionado for ruim para quem usa, tratar na tela e registrar à parte
- [ ] O teste verde com `--repeat-each 10`; verificações do projeto e PR para `main`
