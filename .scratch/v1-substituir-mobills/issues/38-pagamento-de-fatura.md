# Pagamento de fatura

Type: task
Status: ready-for-agent
Blocked by: 37
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #92
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 77, 78, 79, 80, 81

## O que construir

Pagar a fatura é uma transferência da conta para o cartão: o saldo da conta cai no dia do pagamento real e as compras não contam duas vezes ([ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md)).

## Checklist

- [ ] Pagamento de fatura como transferência sem categoria; pagar antes do vencimento ou adiantar com a fatura aberta mexe só no saldo da conta
- [ ] Pagamento parcial: o que faltou vira saldo anterior na fatura seguinte, sem contar de novo no planejamento nem nas tags
- [ ] Juros, IOF e multa do rotativo são lançamentos novos na fatura seguinte
- [ ] Testes de API para saldo, mês da fatura e saldo anterior
- [ ] Verificações do projeto rodando e PR aberto para `main`
