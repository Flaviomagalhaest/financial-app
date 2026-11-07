# Estorno avulso: item na tela, crédito sem fatura, recusa do devido negativo e testes

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #473
Origem: [ticket 152](152-estorno-avulso-pendencias.md): decisões do dono sobre o estorno avulso (adendo do ticket 152 na [ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md))

## O que construir

1. **Item do planejamento na tela do crédito.** "Lançar crédito" (e "Editar crédito") pergunta o item como na compra quando as categorias escolhidas têm dois ou mais itens no mês. Hoje `itemEscolhido` (`web/src/lancamentos/TelaDeLancamento.tsx`) trata o avulso como o estorno ligado e esconde o aviso de planejamento; o estorno ligado continua sem escolha.
2. **Recusa do devido negativo.** `POST` e `PUT /api/lancamentos` recusam (422, com motivo legível) o avulso que deixaria o devido da fatura dele (saldo anterior + compras + ajuste, com os créditos) abaixo de zero. Vale na criação e na edição, inclusive na troca de data ou de fatura. Nenhum outro caminho ganha essa trava (excluir ou mover compra, ajuste, estorno ligado). Sem internet, a recusa aparece na fila como as outras (sem conferência no aparelho).
3. **Mês sem fatura.** "Lançar crédito" aparece em `TelaDaFatura.tsx` em qualquer mês que não esteja pago, mesmo sem fatura criada; a data decide a fatura e o servidor a cria (`garantir_fatura`).
4. **Sinal de crédito na "A escolher".** A linha da Hoje (`web/src/hoje/TelaHoje.tsx`) mostra o valor do estorno (ligado ou avulso) com o sinal de crédito, como as outras listas (`eEstorno`).
5. **Testes que faltam**: o avulso na busca e no histórico (a soma do aparelho em `web/src/dados/busca.ts`), no limite do cartão e na projeção; a tag e a pessoa lançadas pela tela (o e2e `web/e2e/estorno-avulso.spec.ts` só cobre categoria).

## Checklist

- [x] Teste de API: avulso que deixa o devido negativo é recusado na criação e na edição (troca de valor, data e fatura); o que deixa o devido em zero passa
- [x] Teste de API: avulso num mês sem fatura cria a fatura com as datas padrão
- [x] Tela pergunta o item com duas categorias com item; e2e cobre a escolha
- [x] "Lançar crédito" no mês sem fatura; e2e cobre
- [x] Sinal de crédito na "A escolher"
- [x] Testes do avulso na busca, no histórico, no limite e na projeção; tag e pessoa pela tela
