# Saldo da conta conta os não enviados do aparelho

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #155
Origem: [ticket 33](33-lancamento-sem-internet-fila-e-envio.md) (revisão: a história 46 pede o não enviado "já contando no saldo e no aviso de planejamento do meu aparelho", mas o saldo vem pronto do servidor em `GET /api/contas` (`saldo_centavos`, ticket 36) e não vê a fila)

## O que construir

O saldo de cada conta mostrado no aparelho soma, sobre o saldo guardado do servidor, os realizados não enviados da fila de `web/src/dados/`: criar, editar (a diferença) e excluir, só os de data depois do saldo de abertura, como no servidor ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)). Quando a soma inclui não enviados, o saldo leva o ⏳.

## Checklist

- [x] Saldo no aparelho = saldo guardado + efeito da fila, numa função da camada de dados usada por toda tela que mostra saldo
- [x] ⏳ ao lado do saldo que inclui não enviados
- [x] Teste de navegador: sem internet, lançar uma despesa realizada muda o saldo da conta; ao enviar, o saldo do servidor fica igual
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas da implementação

- `web/src/dados/saldo.ts` (`saldoNoAparelho`, sem React) soma, sobre `saldo_centavos`, a diferença entre como cada item da fila fica no aparelho e como o servidor o tem; `useCadastro` e `useContasComArquivadas` entregam as contas já com o saldo do aparelho e `saldoNaoEnviado` (⏳ em `TelaDeContasECategorias`). Só entram lançamentos (transferência precisa de internet); conflito e exclusão pela outra pessoa não mexem; a recusa conta, como na lista.
- Teste de navegador em `web/e2e/sem-internet.spec.ts` (criar, excluir e editar offline; igual ao servidor depois de enviar).
- `cartoes.spec.ts:87` já falhava na `main` (espera pelo token na recarga), sem relação com este ticket.
