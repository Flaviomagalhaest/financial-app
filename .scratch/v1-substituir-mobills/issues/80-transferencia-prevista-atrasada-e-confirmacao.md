# Transferência prevista: atrasada e confirmação

Type: task
Status: ready-for-human
Blocked by: —
Skills: `grilling` para o dono decidir se ela entra nas contas da semana; depois `implement`, `tdd`; HITL na decisão
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #153
Origem: [ticket 43](43-previsto-realizado-e-contas-da-semana.md) (revisão: a transferência do [ticket 36](36-contas-saldo-e-transferencia.md) também pode ser prevista, mas o atrasado e a confirmação só existem para lançamentos)

## O que construir

A história 108 vale para qualquer previsto: "um previsto com data passada sem confirmação fique atrasado". O ticket 43 fez isso só para lançamentos (`atrasado` em `Lancamento`, `POST /api/lancamentos/{id}/confirmar`, `GET /api/contas-da-semana`). A transferência prevista (`backend/app/transferencias.py`) não tem `atrasado`, não se confirma por uma chamada própria (só editando a situação) e não aparece nas contas da semana. A história 109 fala em "despesas e receitas", então a lista pode ficar como está.

## Checklist

- [ ] O dono decide se a transferência prevista entra nas contas da semana (resposta em `## Answer`)
- [ ] `atrasado` na transferência, com a mesma regra do lançamento (previsto com data antes de hoje em São Paulo, `app.lancamentos.hoje`)
- [ ] Confirmar a transferência prevista, ajustando valor e data, com as mesmas regras do lançamento: reenvio igual devolve o gravado e ajuste diferente dá 409
- [ ] Se entrar nas contas da semana: `GET /api/contas-da-semana` e o bloco da Hoje mostram a transferência
- [ ] A tela de transferência (ticket 42, `TelaDeTransferencia.tsx`) não troca a situação à mão: só a data decide, embora a API aceite `situacao`. Dar a ela a troca Realizado/Previsto do lançamento
- [ ] Testes de API, e de navegador se a Hoje mudar
- [ ] Verificações do projeto rodando e PR aberto para `main`
