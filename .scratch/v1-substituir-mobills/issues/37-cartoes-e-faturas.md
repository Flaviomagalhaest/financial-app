# Cartões e faturas

Type: task
Status: ready-for-agent
Blocked by: 36
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #91
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 69, 70, 71, 72, 73, 74, 75, 76, 86

## O que construir

O casal cadastra cartões e cada compra cai na fatura certa pelo fechamento e conta no mês da fatura ([ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md)).

## Checklist

- [ ] Cartões com dia de fechamento e vencimento padrão, limite opcional, regra "mês anterior ao fechamento", cartão adicional ligado ao titular (compras na fatura do titular) e arquivar
- [ ] Fatura por cartão por mês, criada quando a primeira compra precisa dela, com fechamento e vencimento editáveis; compra no próprio dia do fechamento vai para a seguinte; troca manual de fatura
- [ ] Mudar o dia padrão redistribui só faturas abertas e futuras; fatura fechada nunca muda
- [ ] O lançamento grava o mês em que conta (mês da fatura no cartão, a data no resto), com índice por esse mês
- [ ] Teste com o exemplo do glossário: compra de 28/03 em fatura que fecha em 25/04 conta em abril
- [ ] Verificações do projeto rodando e PR aberto para `main`
