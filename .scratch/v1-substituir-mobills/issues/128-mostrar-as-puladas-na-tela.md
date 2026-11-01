# Mostrar na tela as ocorrências e parcelas puladas por estarem no passado

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` (lançar recorrente e parcelado com data passada e ver o aviso)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #302
Origem: revisão (Spec) do [ticket 125](125-geracao-pula-o-passado.md)

## O problema

O `## Answer` do [ticket 87](87-recorrencia-com-inicio-no-passado.md) diz que "a resposta avisa quantas foram puladas". O ticket 125 pôs `parcelas_puladas` no parcelamento da API, mas o app cria pela fila e não mostra a resposta: o casal não fica sabendo. A recorrência com início no passado também não avisa nada.

## Checklist

- [x] Na folha do novo lançamento, recorrente ou parcelado com data antes de hoje: dizer antes de salvar quantas ocorrências ou parcelas não serão lançadas (a conta repete a do servidor só para mostrar, como a ADR 0018)
- [x] Na tela do parcelamento (`TelaDoParcelamento.tsx`), mostrar as puladas pelo `parcelas_puladas`
- [x] Teste de navegador em `web/e2e/`

## Answer

Feito. A folha de detalhes do novo lançamento mostra, antes de salvar, "N ocorrências/parcelas não serão lançadas: caem antes de hoje" (`ocorrenciasPuladas` em `web/src/lancamentos/recorrencia.ts`, `parcelasPuladas` em `parcelamento.ts`; repetem a geração do servidor só para mostrar, ADR 0018). O cartão não pula parcela, então não avisa. A `TelaDoParcelamento.tsx` mostra as puladas pelo `parcelas_puladas`. Testes de navegador em `web/e2e/puladas.spec.ts`.

Pendência: [130](130-tabela-das-puladas.md) (a ADR 0018 pede tabela de casos para a conta repetida no app). Observação (o 422 do boleto já é tema do ticket 129): o servidor responde 422 quando o boleto ou a recorrência inteiros estão no passado; a folha avisa as puladas, mas não trata esse caso à parte.
