# Recorrência e parcelamento enviados no dia seguinte perdem a ocorrência do dia do lançamento

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `codebase-design` (onde entra a data do aparelho), `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #301
Origem: revisão (Spec) do [ticket 125](125-geracao-pula-o-passado.md)

## O problema

A geração (ticket 125) pula o que vem antes do `hoje()` do servidor na hora em que gera. Sem internet, o casal lança no dia D a recorrência ou o boleto cuja 1ª ocorrência é D, e a fila só sobe em D + 1: a ocorrência de D já está no passado e é pulada, em vez de nascer realizada como o `## Answer` do [ticket 87](87-recorrencia-com-inicio-no-passado.md) manda ("a ocorrência de hoje vinda do novo lançamento nasce realizada"). Se a regra termina em D, o envio leva 422 "termina antes de hoje". O mesmo acontece quando a geração para no meio e o reenvio ou a tarefa diária (`completar_todos`) a termina no dia seguinte.

## Checklist

- [ ] O pedido de criação (`POST /api/recorrencias`, `POST /api/parcelamentos` e `criar_*` do lote) leva o dia em que o casal lançou, e "antes de hoje" se conta a partir dele (guardado na regra para a geração que continua depois)
- [ ] O app manda esse dia na fila (`web/src/dados/fila.ts`)
- [ ] Teste de API: criar com o dia de ontem no pedido gera a ocorrência de ontem realizada; teste do navegador sem internet virando o dia, se der
