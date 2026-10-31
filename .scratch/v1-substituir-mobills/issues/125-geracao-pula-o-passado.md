# Recorrência e boleto parcelado pulam as ocorrências anteriores a hoje

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `domain-modeling` para o `GLOSSARY.md`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #296
Origem: [ticket 87](87-recorrencia-com-inicio-no-passado.md) e pergunta 5 do [ticket 99](99-parcelamento-regras-provisorias.md) (decisão do dono, `## Answer` do 87)

## O que construir

Regra decidida: a geração só lança ocorrências de hoje em diante; o calendário continua contado desde o `inicio`.

## Checklist

- [ ] `POST /api/recorrencias`: ocorrências antes de hoje (São Paulo) não geram lançamento, previstas ou automáticas; `ocorrencia_do_inicio` e a contagem de `vezes` não mudam
- [ ] A ocorrência de hoje nasce realizada (estimada e automática)
- [ ] 422 "a recorrência termina antes de hoje" quando `ate` ou o fim por `vezes` cai antes de hoje
- [ ] Tarefa diária e correção da regra seguem a mesma regra (nada retroativo)
- [ ] `POST /api/parcelamentos` em boleto com data no passado: parcelas anteriores a hoje puladas, numeração mantida, total mantido, a de hoje realizada, resposta com o aviso de quantas foram puladas
- [ ] Testes de API em `backend/tests/test_recorrencias.py` e `backend/tests/test_parcelamentos.py`
- [ ] Verbetes do `GLOSSARY.md` atualizados (recorrência, parcelamento)
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Ajuste em `_gerar_um_lote` e na validação de `NovaRecorrencia` (`backend/app/recorrencias.py`) e na geração de `backend/app/parcelamentos.py`.
