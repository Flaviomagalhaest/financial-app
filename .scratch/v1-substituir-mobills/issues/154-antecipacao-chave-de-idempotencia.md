# Antecipação: chave de idempotência para o reenvio

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` se mexer na fila do app
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #373
Origem: [ticket 102](102-antecipacao-regras-provisorias.md) (o dono decidiu adicionar a chave)

## O que construir

`POST /api/parcelamentos/{id}/antecipacoes` aceita uma chave (por exemplo o id da antecipação gerado no aparelho). Repetir o pedido com a mesma chave devolve as parcelas já antecipadas, sem antecipar as K seguintes.

## Checklist

- [ ] Teste de API em `backend/tests/test_parcelamentos.py`: reenvio com a mesma chave não antecipa de novo
- [ ] Ajuste em `_antecipar` (`backend/app/parcelamentos.py`) e rota
- [ ] Fila sem internet do app envia a chave, como `criar_parcelamento` do 46
- [ ] Verbete "Antecipação" do `GLOSSARY.md`
- [ ] Verificações do projeto e PR para `main`
