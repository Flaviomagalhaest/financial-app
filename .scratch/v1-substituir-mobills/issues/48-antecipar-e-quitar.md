# Antecipar parcelas e quitar o restante

Type: task
Status: ready-for-agent
Blocked by: 46
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #102
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 99, 100

## O que construir

O casal registra uma antecipação com desconto ou a quitação do que falta.

## Checklist

- [ ] Antecipar K parcelas tiradas do fim, com data de hoje ou outra e valor editável
- [ ] Quitar o restante de uma vez
- [ ] Testes de API com os totais antes e depois
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Do [ticket 46](46-parcelamento-criar.md): no cartão, a fatura da parcela n vem de `faturas.mes_da_parcela` (n - 1 faturas depois da fatura da compra), e a redistribuição pelas datas do cartão (`cartoes._redistribuir`) e a edição da data a recalculam. A parcela antecipada, que conta na fatura em que foi paga, precisa da marca de troca à mão (`fatura_a_mao`) ou de outra, para não voltar à fatura dela. A tarefa diária realiza a parcela automática pelo `realiza_em` (`backend/app/parcelamentos.py`).
