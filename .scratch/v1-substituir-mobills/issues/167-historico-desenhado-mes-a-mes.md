# Histórico desenhado mês a mês e continuado pelo servidor

Type: task
Status: resolved
Blocked by: 166
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #399
Origem: [ticket 124](124-historico-sem-a-lista-inteira.md) e [ADR 0025](../../../docs/adr/0025-sem-internet-so-a-janela-do-aparelho.md) (decisão Q5).

## O que construir

O Histórico (`ListaDeLancamentos.tsx`) desenha hoje um `<ul>` com todos os lançamentos. Passa a desenhar mês a mês, com cabeçalho de mês: mostra os meses mais recentes e desenha o mês anterior quando a pessoa chega ao fim da tela. Depois do fim da janela do aparelho, com internet, continua lendo do servidor mês a mês, sem guardar no aparelho. Sem internet, o fim da janela mostra "Para ver antes de <mês>, conecte-se à internet".

## Checklist

- [x] Testes de navegador: cabeçalho de mês, o mês anterior ao rolar, a continuação pelo servidor depois da janela e o aviso de fim sem internet
- [x] Voltar ao padrão o prazo do teste "a rede volta, mas a lista não chega antes do envio" (`web/e2e/sem-internet.spec.ts`, `lerAListaInteira`)
- [x] Medir com `web/e2e/medir-historico.ts` (1.600, 6 mil e 11 mil lançamentos, CPU 4x) e registrar aqui o tempo até mostrar

## Resultado

- **Tela**: `ListaDeLancamentos.tsx` desenha um `<section>` por mês, com `<h3>` "MM/AAAA", e um `fim-da-lista` observado por `IntersectionObserver`. A lógica fica em `useHistoricoMesAMes.ts`: de início aparecem todo o futuro (parcelas e previstos), o mês atual e os 2 anteriores; a cada chegada ao fim, mais um mês da janela. O mês com item na fila (não enviado, recusado, em conflito) aparece sempre. Depois do fim da janela, com internet, lê `/api/meses/{mes}/lancamentos` um mês por vez, sem guardar, pulando os meses vazios, até o mês mais antigo. Sem internet, o fim mostra "Para ver antes de MM/AAAA, conecte-se à internet." e tenta de novo quando a rede volta.
- **Servidor**: `GET /api/lancamentos-primeiro-mes` (`{ mes }`, o mês mais antigo em que um lançamento conta, `null` sem lançamentos), com teste em `test_lancamentos_das_telas.py`. Sem ele a tela não saberia até onde ler.
- **Testes**: `web/e2e/historico-mes-a-mes.spec.ts` (3). O prazo de `lerAListaInteira` em `sem-internet.spec.ts` voltou ao padrão. A suíte inteira de navegador passou num banco limpo, menos os testes que falham por causa do banco reaproveitado entre rodadas (não é do ticket).
- **Medida** (`web/e2e/medir-historico.ts`, CPU 4x, 3 rodadas, mediana, recarregar o Histórico até mostrar um lançamento novo; lançamentos no servidor do gerador do ticket 112):

| No servidor | Na janela | Itens de lista na tela | Até mostrar |
|---|---|---|---|
| 1.600 | 177 | 46 | 560 ms |
| 6.000 | 697 | 136 | 834 ms |
| 11.000 | 1.263 | 236 | 1,2 s (1,04 a 1,39) |

  Antes (ticket 166, 11 mil no servidor): 2,7 s com 1.266 itens na tela. O custo agora cresce com o que está desenhado, não com a janela.
