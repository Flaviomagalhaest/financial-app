# Janela do aparelho: guardar só 12 meses e o futuro

Type: task
Status: ready-for-agent
Blocked by: 164, 165
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: high
Issue: #398
Origem: [ticket 124](124-historico-sem-a-lista-inteira.md) e [ADR 0024](../../../docs/adr/0024-sem-internet-so-a-janela-do-aparelho.md) (decisões Q1, Q3, Q4, Q6, Q7).

## O que construir

O aparelho passa a guardar só a **janela do aparelho** (`GLOSSARY.md`): os lançamentos que contam nos últimos 12 meses, pelo mês em que contam (o `mes`, o da fatura na compra no cartão), e todos daqui para frente.

- **Servidor**: `GET /api/lancamentos` devolve só a janela (o `_todos` já aceita filtro SQL). O tamanho (12) vai para `config/valores-iniciais.json`.
- **Aparelho**: relê a janela inteira, como hoje (sem "mudou desde", decisão Q7). O que sai da janela quando o mês vira some do aparelho, menos o que tem mudança não enviada ou conflito.
- **Fora da janela, sem internet**: abrir, editar, estornar, ver a recorrência ou as parcelas de um lançamento que não está no aparelho mostra "Sem internet: este lançamento não está no aparelho" (o texto já existe em `TelaDeLancamento.tsx`). Com internet, a tela lê o lançamento do servidor.
- **Busca sem internet**: olha só a janela e diz "Sem internet: a busca olhou só os últimos 12 meses".
- **`naTela`**: hoje a edição de um item que não está na lista entra como novo e perde campos (`index.ts`, `naTela`). Com a janela isso fica possível (mudança não enviada de um item que saiu): tratar.
- O índice de estornos e o `ultimoCriado` passam a olhar a janela; o estorno de uma compra fora dela pede internet.

## Checklist

- [ ] Testes do backend: a janela pelo `mes`, com a compra no cartão que conta no mês seguinte e os previstos futuros
- [ ] Testes de navegador: lançamento fora da janela sem internet (abrir, estornar, buscar) e com internet
- [ ] Teste do mês que vira com mudança não enviada num lançamento que sai da janela
- [ ] Medir com `web/e2e/medir-historico.ts` com 11 mil lançamentos no servidor e registrar aqui
