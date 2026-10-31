# Mostrar na tela as ocorrências e parcelas puladas por estarem no passado

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` (lançar recorrente e parcelado com data passada e ver o aviso)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #302
Origem: revisão (Spec) do [ticket 125](125-geracao-pula-o-passado.md)

## O problema

O `## Answer` do [ticket 87](87-recorrencia-com-inicio-no-passado.md) diz que "a resposta avisa quantas foram puladas". O ticket 125 pôs `parcelas_puladas` no parcelamento da API, mas o app cria pela fila e não mostra a resposta: o casal não fica sabendo. A recorrência com início no passado também não avisa nada.

## Checklist

- [ ] Na folha do novo lançamento, recorrente ou parcelado com data antes de hoje: dizer antes de salvar quantas ocorrências ou parcelas não serão lançadas (a conta repete a do servidor só para mostrar, como a ADR 0018)
- [ ] Na tela do parcelamento (`TelaDoParcelamento.tsx`), mostrar as puladas pelo `parcelas_puladas`
- [ ] Teste de navegador em `web/e2e/`
