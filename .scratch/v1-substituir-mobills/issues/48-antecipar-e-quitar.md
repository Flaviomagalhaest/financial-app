# Antecipar parcelas e quitar o restante

Type: task
Status: resolved
Blocked by: 46
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #102
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 99, 100

## O que construir

O casal registra uma antecipação com desconto ou a quitação do que falta.

## Checklist

- [x] Antecipar K parcelas tiradas do fim, com data de hoje ou outra e valor editável
- [x] Quitar o restante de uma vez
- [x] Testes de API com os totais antes e depois
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Do [ticket 46](46-parcelamento-criar.md): no cartão, a fatura da parcela n vem de `faturas.mes_da_parcela` (n - 1 faturas depois da fatura da compra), e a redistribuição pelas datas do cartão (`cartoes._redistribuir`) e a edição da data a recalculam. A parcela antecipada, que conta na fatura em que foi paga, precisa da marca de troca à mão (`fatura_a_mao`) ou de outra, para não voltar à fatura dela. A tarefa diária realiza a parcela automática pelo `realiza_em` (`backend/app/parcelamentos.py`).
- API em `backend/app/parcelamentos.py`: `POST /api/parcelamentos/{id}/antecipacoes` (`parcelas`, `data` opcional, `valor_total_centavos` opcional) e `POST /api/parcelamentos/{id}/quitacao` (`data` e `valor_total_centavos` opcionais). Paga as últimas K parcelas previstas (a quitação, todas): cada uma vira realizada na data do pagamento, com o valor informado dividido entre elas (centavos que sobram na primeira antecipada); sem valor, o das próprias parcelas. No cartão, a parcela passa à fatura que fecha depois do dia do pagamento, com `fatura_a_mao`, e as datas do cartão não a levam de volta. A resposta traz só as parcelas antecipadas. A data futura é recusada.
- Pendências: as regras provisórias (data futura, valor total, `data` da parcela trocada, reenvio sem chave, quitar sem nada a pagar) são decisão do dono no [ticket 102](102-antecipacao-regras-provisorias.md). A tela e a fila do app ficam com o [ticket 98](98-parcelamento-criar-pela-tela-e-sem-internet.md) e os tickets de tela do parcelamento.
