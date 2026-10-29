# Pagamento de fatura

Type: task
Status: resolved
Blocked by: 37
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #92
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 77, 78, 79, 80, 81

## O que construir

Pagar a fatura é uma transferência da conta para o cartão: o saldo da conta cai no dia do pagamento real e as compras não contam duas vezes ([ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md)).

## Checklist

- [x] Pagamento de fatura como transferência sem categoria; pagar antes do vencimento ou adiantar com a fatura aberta mexe só no saldo da conta
- [x] Pagamento parcial: o que faltou vira saldo anterior na fatura seguinte, sem contar de novo no planejamento nem nas tags
- [x] Juros, IOF e multa do rotativo são lançamentos novos na fatura seguinte
- [x] A fatura (`Fatura` em `backend/app/cartoes.py`, ticket 37) tem `situacao` aberta ou fechada: acrescentar `paga`, e o pagamento parte de `transferencias` com o cartão como destino (`conferir_conta` hoje só aceita conta); no CSV de planilha (`ler_lancamentos`, ticket 77) o pagamento sai como as transferências, com o cartão no destino
- [x] Testes de API para saldo, mês da fatura e saldo anterior
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Modelo: o pagamento é uma linha de `transferencias` com o cartão em `conta_destino_id` e o mês da fatura em `fatura_mes` (migration `0036`, backup na versão 13 com o conversor da 12; [ADR 0014](../../../docs/adr/0014-transferencia-em-tabela-propria.md)). `POST/PUT /api/transferencias`: com destino num cartão o `fatura_mes` é obrigatório e a fatura precisa existir; categoria é recusada (422); `fatura_mes` com destino numa conta é recusado; cartão arquivado só segue num pagamento que já existia. Pagar o cartão adicional quita a fatura do titular.
- Saldo: o da conta não mudou, porque o cartão nunca é uma `contas.id`; o pagamento realizado tira da conta no dia dele, antes ou depois do vencimento, e não mexe no `mes` de nenhuma compra. O previsto não mexe no saldo nem conta como pago.
- Faturas (`GET /api/cartoes/{id}/faturas` e o `PATCH`): ganharam `total_centavos` (despesas menos receitas, previstas e realizadas), `saldo_anterior_centavos`, `pago_centavos`, `a_pagar_centavos` (saldo anterior mais total menos pago, sem passar de zero) e a situação `paga` (fechada e quitada). O saldo anterior de uma fatura é o `a_pagar` da fatura existente anterior, só quando ela já fechou; não é lançamento, então não entra em planejamento, categoria nem tag.
- Juros, IOF e multa do rotativo são compras comuns no cartão (com a categoria que o casal escolher), na fatura seguinte pela data ou pela troca à mão; não houve código novo, só o teste.
- Planilha: a linha do pagamento mostra a fatura que ele quita (`AAAA-MM`) e "Conta → Cartão".
- Provisórios para o dono conferir no [ticket 89](89-conferir-as-regras-de-fatura.md): pagamento a mais que o devido não vira crédito; a fatura aberta não passa saldo; fatura de mês sem compra não nasce e fica sem como receber o saldo anterior (ele vai para a próxima que existir).
- Fora deste ticket: a tela de pagar fatura e a situação "paga" na aba Cartões ([55](55-aba-cartoes.md)), o "comprometido" e o "disponível" ([23](23-limite-comprometido-do-cartao.md)), estorno e ajuste de fatura ([39](39-estorno-ajuste-de-fatura-e-cancelamento.md)).
