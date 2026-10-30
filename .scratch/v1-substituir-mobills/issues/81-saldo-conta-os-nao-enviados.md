# Saldo da conta conta os não enviados do aparelho

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #155
Origem: [ticket 33](33-lancamento-sem-internet-fila-e-envio.md) (revisão: a história 46 pede o não enviado "já contando no saldo e no aviso de planejamento do meu aparelho", mas o saldo vem pronto do servidor em `GET /api/contas` (`saldo_centavos`, ticket 36) e não vê a fila)

## O que construir

O saldo de cada conta mostrado no aparelho soma, sobre o saldo guardado do servidor, os realizados não enviados da fila de `web/src/dados/`: criar, editar (a diferença) e excluir, só os de data depois do saldo de abertura, como no servidor ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)). Quando a soma inclui não enviados, o saldo leva o ⏳.

## Checklist

- [ ] Saldo no aparelho = saldo guardado + efeito da fila, numa função da camada de dados usada por toda tela que mostra saldo
- [ ] ⏳ ao lado do saldo que inclui não enviados
- [ ] Teste de navegador: sem internet, lançar uma despesa realizada muda o saldo da conta; ao enviar, o saldo do servidor fica igual
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Do [ticket 83](83-confirmar-previsto-sem-internet-pela-fila.md): a fila ganhou o item `confirmar` (o previsto vira realizado, com os ajustes de valor, data e conta), que também entra no saldo do aparelho como realizado novo. E o "ainda dá para gastar" da Hoje vem da leitura guardada de `GET /api/hoje`: o ajuste de valor de uma confirmação não enviada (ou qualquer outro não enviado) só aparece nele depois do envio. É o mesmo "aviso de planejamento do meu aparelho" da história 46.
