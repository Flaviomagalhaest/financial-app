# Recorrência e boleto parcelado pulam as ocorrências anteriores a hoje

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `domain-modeling` para o `GLOSSARY.md`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #296
Origem: [ticket 87](87-recorrencia-com-inicio-no-passado.md) e pergunta 5 do [ticket 99](99-parcelamento-regras-provisorias.md) (decisão do dono, `## Answer` do 87)

## O que construir

Regra decidida: a geração só lança ocorrências de hoje em diante; o calendário continua contado desde o `inicio`.

## Checklist

- [x] `POST /api/recorrencias`: ocorrências antes de hoje (São Paulo) não geram lançamento, previstas ou automáticas; `ocorrencia_do_inicio` e a contagem de `vezes` não mudam
- [x] A ocorrência de hoje nasce realizada (estimada e automática)
- [x] 422 "a recorrência termina antes de hoje" quando `ate` ou o fim por `vezes` cai antes de hoje
- [x] Tarefa diária e correção da regra seguem a mesma regra (nada retroativo)
- [x] `POST /api/parcelamentos` em boleto com data no passado: parcelas anteriores a hoje puladas, numeração mantida, total mantido, a de hoje realizada, resposta com o aviso de quantas foram puladas
- [x] Testes de API em `backend/tests/test_recorrencias.py` e `backend/tests/test_parcelamentos.py`
- [x] Verbetes do `GLOSSARY.md` atualizados (recorrência, parcelamento)
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Ajuste em `_gerar_um_lote` e na validação de `NovaRecorrencia` (`backend/app/recorrencias.py`) e na geração de `backend/app/parcelamentos.py`.

## Answer

Feito. A geração (`_gerar_um_lote` de `backend/app/recorrencias.py` e de `backend/app/parcelamentos.py`) só lança de hoje (São Paulo) em diante: `geradas` passa pelas ocorrências e parcelas de antes de hoje sem lançá-las, então a numeração, o calendário e as `vezes` não mudam. A de hoje nasce realizada quando vem da criação (rota ou lote da fila). A recorrência que termina antes de hoje dá 422 "a recorrência termina antes de hoje". O parcelamento traz `parcelas_puladas` (contado das parcelas geradas sem lançamento) e, por analogia, o boleto que já venceu inteiro dá 422 "o parcelamento termina antes de hoje". O cartão gera todas, como antes. Os testes do comportamento antigo (automático realizando o passado, atrasados gerados pelo início no passado) foram trocados pelos da regra nova, e os testes de navegador de parcelamento e de edição em lote passaram a lançar o boleto hoje.

Pendências: [126](126-correcao-com-parcelas-puladas.md) (a correção do boleto perde parcelas puladas e ainda realiza automáticas retroativas), [127](127-envio-no-dia-seguinte-perde-a-de-hoje.md) (o envio da fila no dia seguinte perde a ocorrência do dia do lançamento), [128](128-mostrar-as-puladas-na-tela.md) (o app não mostra as puladas) e [129](129-conferir-escolhas-do-125.md) (escolhas sem decisão do dono: 422 do boleto, a de hoje no fixo não automático, o nome "pulada", ADR).
