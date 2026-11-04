# Janela do aparelho: guardar só 12 meses e o futuro

Type: task
Status: resolved
Blocked by: 164, 165
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: high
Issue: #398
Origem: [ticket 124](124-historico-sem-a-lista-inteira.md) e [ADR 0025](../../../docs/adr/0025-sem-internet-so-a-janela-do-aparelho.md) (decisões Q1, Q3, Q4, Q6, Q7).

## O que construir

O aparelho passa a guardar só a **janela do aparelho** (`GLOSSARY.md`): os lançamentos que contam nos últimos 12 meses, pelo mês em que contam (o `mes`, o da fatura na compra no cartão), e todos daqui para frente.

- **Servidor**: `GET /api/lancamentos` devolve só a janela (o `_todos` já aceita filtro SQL). O tamanho (12) vai para `config/valores-iniciais.json`.
- **Aparelho**: relê a janela inteira, como hoje (sem "mudou desde", decisão Q7). O que sai da janela quando o mês vira some do aparelho, menos o que tem mudança não enviada ou conflito.
- **Fora da janela, sem internet**: abrir, editar, estornar, ver a recorrência ou as parcelas de um lançamento que não está no aparelho mostra "Sem internet: este lançamento não está no aparelho" (o texto já existe em `TelaDeLancamento.tsx`). Com internet, a tela lê o lançamento do servidor.
- **Busca sem internet**: olha só a janela e diz "Sem internet: a busca olhou só os últimos 12 meses".
- **`naTela`**: hoje a edição de um item que não está na lista entra como novo e perde campos (`index.ts`, `naTela`). Com a janela isso fica possível (mudança não enviada de um item que saiu): tratar.
- O índice de estornos e o `ultimoCriado` passam a olhar a janela; o estorno de uma compra fora dela pede internet.

## Checklist

- [x] Testes do backend: a janela pelo `mes`, com a compra no cartão que conta no mês seguinte e os previstos futuros
- [x] Testes de navegador: lançamento fora da janela sem internet (abrir, estornar, buscar) e com internet
- [x] Teste do mês que vira com mudança não enviada num lançamento que sai da janela
- [x] Medir com `web/e2e/medir-historico.ts` com 11 mil lançamentos no servidor e registrar aqui

## Resultado

- **Servidor**: `GET /api/lancamentos` devolve os lançamentos com `mes` (o mês em que contam) a partir de `inicio_da_janela()`: o mês de hoje (São Paulo) e os 11 antes dele, com `janelaDoAparelhoMeses: 12` em `config/valores-iniciais.json`. Do futuro não há corte. `GET /api/lancamentos/{id}` (novo) lê um lançamento de fora da janela, com os `ligados` a ele pelo estorno: os estornos dele, a compra do estorno e, na parcela, as outras parcelas, os estornos delas e os de todas as parcelas. Assim a tela de estorno calcula o que ainda dá para estornar. Excluído ou inexistente dá 404.
- **Aparelho**: a leitura da lista apaga o que saiu da janela, menos o lançamento com item na fila (não enviado, recusado ou em conflito) (`guardarALista`, `armazem.ts`). A mudança na fila de um lançamento que não está na lista vale sobre a `base` dela (`baseDaMudanca`): no `naTela` (não entra mais como novo nem perde campos), no saldo, no aviso de planejamento e no saldo guardado do envio. O lançamento aceito que conta antes da janela não volta para a lista (`aplicar`, `fila.ts`).
- **Telas**: `useLancamentosComOsDeFora` (`dados/index.ts`) junta à janela, com internet, o lançamento que falta e os ligados a ele, lidos do servidor sem guardar, e diz se está lendo, se faltou internet ou se ele não existe. A tela de lançamento (abrir, editar), a do estorno e a da recorrência o usam. Sem internet, dizem "Sem internet: este lançamento não está no aparelho." (no estorno, "esta compra", o texto que já existia) e tentam de novo quando a rede volta. A busca sem internet diz "Sem internet: a busca olhou só os últimos 12 meses." O índice de estornos da fatura junta a janela e as compras da fatura. O `ultimoCriado` e os outros índices já olham a janela, porque a lista guardada é ela.
- **Testes**: `backend/tests/test_janela_do_aparelho.py` (7). Dois testes de `test_recorrencias.py` andam anos no tempo e liam pela lista o começo da regra; eles passam a ler sem a janela (`sem_a_janela`). `web/e2e/janela-do-aparelho.spec.ts` (5): abrir e editar fora da janela com e sem internet, estornar, buscar, o mês que vira com mudança não enviada e a edição sem resposta de uma parcela fora da janela (o "01/03" só existe na versão do servidor). Conferi que os dois últimos ficam vermelhos sem a correção.
- **Medida** (`web/e2e/medir-historico.ts`, 11.000 lançamentos do gerador do ticket 112 no servidor, CPU 4x mais lenta, 3 rodadas, recarregar o Histórico até mostrar um lançamento novo):

| | ticket 164 (3.000 no servidor, lista inteira) | 166 (11.000 no servidor) |
|---|---|---|
| lançamentos na lista | 3.000 | 1.266 (a janela) |
| resposta da lista | uns 2 MB | 1,0 MB, 72 KB com gzip |
| até mostrar (mediana) | 7,2 s | 2,7 s (2,5 a 3,7) |
| leituras da lista guardada por abertura | 6 | 6 |
| lançamentos gravados na releitura | 1 | 1 |

  O que sobra é o render dos 1.266 itens (JS, layout e estilo somam uns 2 s), que é o [ticket 167](167-historico-desenhado-mes-a-mes.md).
- **Pendências**: [ticket 176](176-janela-do-aparelho-o-que-ficou-de-fora.md). Lá estão o estorno na fatura antiga, o restante do estorno de parcela com as primeiras fora da janela, os testes do mês que vira com conflito e da recorrência fora da janela, a edição sem `base`, o "Repetir último" e um teste de `sem-internet.spec.ts` que falha na nuvem também na `main`.
