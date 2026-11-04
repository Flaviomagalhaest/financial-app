# Teste de navegador da antecipação sem internet é intermitente

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`, `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #435
Origem: sessão do [ticket 170](170-exclusao-do-parcelamento-deixa-as-de-fatura-paga.md) (04/11), que não mexe na antecipação.

## O que falha

`web/e2e/parcelamento.spec.ts`, teste "antecipa parcelas sem internet: fica na fila e o reenvio com a mesma chave não antecipa as seguintes". Rodando localmente (`--repeat-each 2`), falhou uma vez em duas: o clique em `getByRole('region', { name: 'Antecipar ou quitar' }).getByRole('button', { name: 'Quitar tudo' })` esperou os 90 s e o botão não apareceu. Na outra rodada passou em 2,5 s. Não está claro se a `main` falha igual nem se é o mesmo caso do [ticket 120](120-testes-sem-internet-intermitentes.md).

## Checklist

- [ ] Reproduzir na `main` (`npx playwright test e2e/parcelamento.spec.ts -g "antecipa parcelas sem internet" --repeat-each 10`)
- [ ] Achar a causa (a região que não aparece: a tela sem a lista das parcelas? sem internet antes da leitura?)
- [ ] Corrigir sem aumentar espera nem desligar o teste; repetir 10 vezes verde
