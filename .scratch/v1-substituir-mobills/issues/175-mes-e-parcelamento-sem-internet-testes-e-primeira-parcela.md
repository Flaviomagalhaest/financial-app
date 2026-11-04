# Mês e parcelamento sem internet: testes que faltam e primeira parcela fora da janela

Type: task
Status: resolved
Blocked by: 166
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #419
Origem: revisão do [ticket 165](165-telas-que-filtram-a-lista-leem-do-servidor.md) (PR #404): o que o 165 não cobriu e só dá para fechar com a [janela do aparelho](166-janela-do-aparelho.md).

## O que construir

- **Testes de navegador do Mês**: o 165 testa só o Ranking com internet. Faltam: Mês sem internet com a resposta guardada (mostra a última leitura e avisa), Mês sem internet e sem resposta guardada (diz que precisa de internet no "A escolher" e no Ranking), e um lançamento não enviado aparecendo no "A escolher" e no Ranking sem internet.
- **Primeira parcela**: `Correcao` em `TelaDoParcelamento.tsx` usa `doParcelamento[0]` como a 1ª parcela (aviso de planejamento, valor da primeira, `noCartao`). Com a janela do aparelho, a lista da tela vem do servidor e tem todas as parcelas, mas sem internet e com a resposta guardada velha, ou com só os não enviados, `[0]` pode ser uma parcela do meio. Pegar a de menor `parcela` e, sem ela, não mostrar o aviso em vez de calcular com a errada.

## Checklist

- [x] Teste de navegador: Mês sem internet com e sem resposta guardada
- [x] Teste de navegador: não enviado no "A escolher" e no Ranking sem internet
- [x] Primeira parcela escolhida pelo número, não pela posição; sem ela, sem aviso
- [x] Teste de navegador do parcelamento com a lista sem a 1ª parcela
