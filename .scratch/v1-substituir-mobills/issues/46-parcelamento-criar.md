# Parcelamento: criar

Type: task
Status: ready-for-agent
Blocked by: 37, 43
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #100
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 95, 96, 97, 98, 45, 105

## O que construir

O casal lança uma compra ou dívida em N parcelas, no cartão ou em boleto, também sem internet; cada parcela é um lançamento e a compra parcelada não é.

## Checklist

- [ ] Informar valor total ou da parcela; os centavos que sobram vão para a 1ª parcela
- [ ] No cartão, cada parcela conta no mês da fatura em que cai e nasce automática; em boleto, parcelamento fora do cartão
- [ ] Sem internet vai como um pedido só, gerado pelo servidor
- [ ] Testes de API com divisão de centavos e viradas de fatura
- [ ] Verificações do projeto rodando e PR aberto para `main`
- [ ] Parcela automática não pede confirmação (ticket 43): gravar `lancamentos.automatico = true` na parcela, que já a tira de `GET /api/contas-da-semana` e do `atrasado` (ticket 44), e fazer a tarefa diária (`realizar_automaticos` em `backend/app/recorrencias.py`, que hoje só acha os previstos com `recorrencia_id`) realizar também as parcelas, com a `origem` do parcelamento
