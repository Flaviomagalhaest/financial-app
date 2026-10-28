# Contas, saldo de abertura e transferência

Type: task
Status: resolved
Blocked by: 32
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #90
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 63, 64, 65, 66, 67, 68

## O que construir

O casal cadastra contas (corrente, poupança, carteira), informa o saldo de abertura e transfere entre elas; o saldo mostrado bate com o extrato.

## Checklist

- [x] Contas com saldo de abertura e data; só realizados depois dessa data mexem no saldo, e o histórico anterior serve às estatísticas sem alterá-lo
- [x] Tipo transferência entre duas contas, sem contar como despesa, com categoria opcional da lista de transferência
- [x] Arquivar conta tira das opções e mantém o histórico
- [x] Testes de API com exemplos concretos de saldo antes e depois do saldo de abertura
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Contas: `saldo_abertura_centavos` e `data_abertura` (juntos ou nenhum), `PUT /api/contas/{id}` para editar e arquivar, `GET /api/contas[?arquivadas=true]` com `saldo_centavos`. O saldo é a abertura mais os realizados com data **depois** da de abertura (no dia já está no valor informado); sem abertura, todos os realizados a partir de zero. Conta arquivada recusa lançamento e transferência novos (422), mas o histórico dela segue editável.
- Transferência em tabela própria, `/api/transferencias`: [ADR 0014](../../../docs/adr/0014-transferencia-em-tabela-propria.md). Categoria opcional, da lista de transferência.
- Backup na versão 3, com o conversor da 2 (contas sem abertura e `transferencias` vazia).
- Fora deste ticket, de propósito: as telas de contas e transferência. As de contas ficam no [ticket 74](74-cadastro-provisorio-de-contas-e-categorias.md); a de lançar uma transferência não tem ticket e entra com a jornada do [ticket 42](42-jornada-completa-do-lancamento-rapido.md). A busca e o histórico ainda não listam transferências (ADR 0014).
