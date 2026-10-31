# Transferência prevista: atrasada e confirmação

Type: task
Status: resolved
Blocked by: —
Skills: `grilling` (feito) para o dono decidir se ela entra nas contas da semana; depois `implement`, `tdd`; HITL na decisão
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #153
Origem: [ticket 43](43-previsto-realizado-e-contas-da-semana.md) (revisão: a transferência do [ticket 36](36-contas-saldo-e-transferencia.md) também pode ser prevista, mas o atrasado e a confirmação só existem para lançamentos)

## O que construir

A história 108 vale para qualquer previsto: "um previsto com data passada sem confirmação fique atrasado". O ticket 43 fez isso só para lançamentos (`atrasado` em `Lancamento`, `POST /api/lancamentos/{id}/confirmar`, `GET /api/contas-da-semana`). A transferência prevista (`backend/app/transferencias.py`) não tem `atrasado`, não se confirma por uma chamada própria (só editando a situação) e não aparece nas contas da semana. A história 109 fala em "despesas e receitas", então a lista pode ficar como está.

## Checklist

- [x] O dono decide se a transferência prevista entra nas contas da semana (resposta em `## Answer`)
- [x] `atrasado` na transferência, com a mesma regra do lançamento (previsto com data antes de hoje em São Paulo, `app.lancamentos.hoje`)
- [x] Confirmar a transferência prevista, ajustando valor e data, com as mesmas regras do lançamento: reenvio igual devolve o gravado e ajuste diferente dá 409
- [x] Se entrar nas contas da semana: `GET /api/contas-da-semana` e o bloco da Hoje mostram a transferência
- [x] A tela de transferência (ticket 42, `TelaDeTransferencia.tsx`) não troca a situação à mão: só a data decide, embora a API aceite `situacao`. Dar a ela a troca Realizado/Previsto do lançamento
- [x] Testes de API, e de navegador se a Hoje mudar
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

O dono decidiu (grilling):

- A transferência prevista **entra** nas contas da semana, inclusive o pagamento de fatura previsto.
- A tela de transferência ganha a troca Realizado/Previsto do lançamento; trocar a data volta à inferência pela data.
- O selo "atrasado" aparece nas contas da semana e na linha da transferência da busca (a lista de lançamentos não tem selo).

Feito: `atrasado` em `Transferencia`; `POST /api/transferencias/{id}/confirmar` (valor e data; reenvio igual devolve o gravado, ajuste diferente de uma já realizada dá 409); `transferencias_da_semana` em `GET /api/hoje`, que o bloco mostra com "Confirmar" e "Ajustar". A confirmação só com internet (ADR 0011); a versão pela fila ficou no [ticket 124](124-confirmar-transferencia-sem-internet.md).
