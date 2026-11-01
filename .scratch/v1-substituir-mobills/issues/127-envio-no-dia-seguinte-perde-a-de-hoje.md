# Recorrência e parcelamento enviados no dia seguinte perdem a ocorrência do dia do lançamento

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `codebase-design` (onde entra a data do aparelho), `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #301
Origem: revisão (Spec) do [ticket 125](125-geracao-pula-o-passado.md)

## O problema

A geração (ticket 125) pula o que vem antes do `hoje()` do servidor na hora em que gera. Sem internet, o casal lança no dia D a recorrência ou o boleto cuja 1ª ocorrência é D, e a fila só sobe em D + 1: a ocorrência de D já está no passado e é pulada, em vez de nascer realizada como o `## Answer` do [ticket 87](87-recorrencia-com-inicio-no-passado.md) manda ("a ocorrência de hoje vinda do novo lançamento nasce realizada"). Se a regra termina em D, o envio leva 422 "termina antes de hoje". O mesmo acontece quando a geração para no meio e o reenvio ou a tarefa diária (`completar_todos`) a termina no dia seguinte.

## Checklist

- [x] O pedido de criação (`POST /api/recorrencias`, `POST /api/parcelamentos` e `criar_*` do lote) leva o dia em que o casal lançou, e "antes de hoje" se conta a partir dele (guardado na regra para a geração que continua depois)
- [x] O app manda esse dia na fila (`web/src/dados/fila.ts`)
- [x] Teste de API: criar com o dia de ontem no pedido gera a ocorrência de ontem realizada; teste do navegador sem internet virando o dia, se der
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

Feito. `NovaRecorrencia` e `NovoParcelamento` ganham `dia_do_lancamento` (opcional): o dia, em São Paulo, em que o casal lançou. Sem ele vale o da chegada, e depois de hoje (relógio adiantado) vale hoje (`com_o_dia_do_lancamento`). Ele fica gravado na regra (migrations 0056 e 0057, backup na versão 23 com o conversor da 22) e volta na resposta. Enquanto a regra é a que o casal lançou (`alterado_em = criado_em`, em `dia_do_lancamento_vigente`), a geração conta o "antes de hoje" desse dia, inclusive quando o reenvio ou a tarefa diária terminam a geração parada; a ocorrência ou a parcela do boleto desse dia nasce realizada, e a regra que termina nele não é mais recusada. Mudada a regra (PATCH, correção), a geração volta a contar de hoje e nada se gera para trás. O `na_criacao` saiu: quem diz "lançada agora" é o dia gravado. A fila (`acoesDo` em `web/src/dados/fila.ts`) manda o dia de `desde`, quando o pedido entrou nela. Testes de API em `test_recorrencias.py` e `test_parcelamentos.py` (rota, lote, fim no dia do lançamento, relógio adiantado, tarefa diária terminando a geração parada, regra mudada) e de navegador em `web/e2e/recorrencia.spec.ts` (sem internet ontem, enviada hoje); o do boleto ficou só na API.

Pendência: [130](130-edicao-em-lote-perde-o-dia-do-lancamento.md) (a edição em lote no meio de uma geração parada muda `alterado_em` e o parcelamento perde o dia do lançamento).
