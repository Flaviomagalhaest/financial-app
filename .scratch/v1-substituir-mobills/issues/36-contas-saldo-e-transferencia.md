# Contas, saldo de abertura e transferência

Type: task
Status: ready-for-agent
Blocked by: 32
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #90
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 63, 64, 65, 66, 67, 68

## O que construir

O casal cadastra contas (corrente, poupança, carteira), informa o saldo de abertura e transfere entre elas; o saldo mostrado bate com o extrato.

## Checklist

- [ ] Contas com saldo de abertura e data; só realizados depois dessa data mexem no saldo, e o histórico anterior serve às estatísticas sem alterá-lo
- [ ] Tipo transferência entre duas contas, sem contar como despesa, com categoria opcional da lista de transferência
- [ ] Arquivar conta tira das opções e mantém o histórico
- [ ] Testes de API com exemplos concretos de saldo antes e depois do saldo de abertura
- [ ] Verificações do projeto rodando e PR aberto para `main`
