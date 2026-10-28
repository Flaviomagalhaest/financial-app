# Confirmar previsto sem internet pela fila

Type: task
Status: ready-for-agent
Blocked by: 43
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Opus
Effort recomendado: high
Issue: #157
Origem: [ticket 33](33-lancamento-sem-internet-fila-e-envio.md) (a história 44 pede confirmar sem internet; a fila do 33 leva criar, editar e excluir, e a confirmação do [ticket 43](43-previsto-realizado-e-contas-da-semana.md), em `POST /api/lancamentos/{id}/confirmar`, e o bloco `ContasDaSemana` falam direto com a API)

## O que construir

Confirmar um previsto (com ou sem ajuste de valor, data e conta) entra na fila de `web/src/dados/` e sobe no lote, como as outras mudanças ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)).

## Checklist

- [ ] Ação `confirmar` em `POST /api/lancamentos/lote`, com as regras da rota de confirmar do ticket 43 (ajuste opcional; reenvio igual devolve o gravado; ajuste diferente sobre um já confirmado vira o resultado que o ticket 34 definir para conflito)
- [ ] Na fila (no máximo uma mudança por lançamento): confirmar o que ainda não subiu muda o pedido que já está lá; o aparelho mostra o lançamento como realizado ⏳
- [ ] `ContasDaSemana` lê e escreve pela camada de dados, com "atualizado às" sem internet
- [ ] Teste de navegador: confirmar sem internet, ⏳, envio sem duplicar
- [ ] Verificações do projeto rodando e PR aberto para `main`
