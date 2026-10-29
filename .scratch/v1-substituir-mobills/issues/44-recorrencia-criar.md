# Recorrência: criar

Type: task
Status: resolved
Blocked by: 43
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #98
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 87, 88, 89, 105, 106

## O que construir

O casal cadastra o salário, a luz ou o seguro anual uma vez só e os previstos aparecem sozinhos.

## Checklist

- [x] Recorrência a cada N semanas ou N meses, sem fim, até uma data ou por N vezes; dia 31 em mês curto cai no último dia
- [x] Valor fixo ou estimado; só a de valor fixo pode ser automática (vira realizada sozinha na data); a estimada sempre pede confirmação
- [x] Previstos gerados até o horizonte de 24 meses, estendido por uma tarefa diária (EventBridge) que também realiza os automáticos
- [x] Testes de API com datas de fim de mês e com a tarefa diária
- [x] Verificações do projeto rodando e PR aberto para `main`
- [x] Previsto automático não pede confirmação (ticket 43): fica fora de `GET /api/contas-da-semana` e não aparece como `atrasado`, que hoje valem para todo `situacao = 'previsto'`

## Notas

- API em `backend/app/recorrencias.py`: `POST /api/recorrencias` (id gerado no aparelho; o reenvio devolve a gravada com 200) e `GET /api/recorrencias`. A regra tem `a_cada` + `unidade` (`semanas` ou `meses`; anual é 12 meses), `inicio`, e `ate` ou `vezes` (nenhum dos dois: sem fim). `tipo_do_valor` é `fixo` ou `estimado`, e `automatico` só vale no fixo (422 no estimado). A data de cada ocorrência é contada do início, nunca da anterior, então o 31 passa por 30/11, 28 ou 29/02 e volta a 31.
- Os previstos são lançamentos comuns com `recorrencia_id`, `ocorrencia` e `automatico` (migrations 0022 a 0028, backup na versão 10 com o conversor da 9); eles herdam da regra valor, descrição, conta, categorias, tags e pessoa. O id de cada um é `uuid5(regra, número)` e `recorrencias.geradas` guarda até onde gerou: gerar de novo não duplica, e o previsto excluído não volta. A geração vai em lotes de uma transação (`LINHAS_POR_LOTE` dividido pelas linhas de cada previsto), porque o DSQL limita as linhas por transação; se parar no meio, o reenvio ou a tarefa diária continuam.
- Horizonte: hoje (São Paulo) + `horizonteDaRecorrenciaMeses` (24). Mesmo com `vezes`, nada passa do horizonte até a tarefa diária o estender.
- Automático: o de data até hoje já nasce realizado; o futuro nasce previsto com `automatico`, fica fora de `GET /api/contas-da-semana` e nunca é `atrasado`. A tarefa diária (`app.tarefa_diaria.handler`, Lambda `TarefaDiaria` às 00:07 de São Paulo pelo EventBridge Scheduler, papel `api` do DSQL, alarme por e-mail se falhar) estende o horizonte de todas as regras e realiza os automáticos com data até hoje, subindo a versão e gravando a `origem` "a recorrência <descrição>" na versão do campo, que a tela de conflito mostra.
- Interface e fila ficaram para o [ticket 86](86-recorrencia-criar-pela-tela-e-sem-internet.md); o que fazer com o início no passado é decisão do dono no [87](87-recorrencia-com-inicio-no-passado.md). Pendências gravadas também nos [35](35-teste-nos-dois-celulares.md) (conferir a geração e a tarefa no DSQL), [45](45-recorrencia-mudar.md) (como achar os previstos da regra, conta ou categoria arquivada depois, `registrar_mudancas` e `origem` agora públicos) e [46](46-parcelamento-criar.md) (a parcela automática usa a mesma coluna e a tarefa diária precisa realizá-la).
