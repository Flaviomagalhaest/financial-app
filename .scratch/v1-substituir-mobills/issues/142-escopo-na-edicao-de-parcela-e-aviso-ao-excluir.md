# Escopo na edição de parcela e aviso forte ao excluir parcelamento

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `domain-modeling` para o `GLOSSARY.md`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #338
Origem: perguntas 7 e 8 do [ticket 99](99-parcelamento-regras-provisorias.md) (decisão do dono, `## Answer` do 99)

## O que construir

1. ~~**Escopo na edição.**~~ Saiu deste ticket (decisão do dono no [ticket 146](146-escopo-na-parcela-e-a-classificacao-editada-a-mao.md)): o [ticket 136](136-alcance-da-mudanca-na-parcela.md) fez o alcance na edição da parcela, preservando a classificação alterada à mão, e o número de parcelas e o total ficam com a correção do parcelamento. O texto original: Editar uma parcela pergunta o escopo: **só esta**, **esta e as futuras** ou **todas (inclusive as realizadas)**. A descrição, as categorias, as tags, a pessoa e o item valem para as parcelas do escopo, inclusive as editadas à mão; valor, data, conta e fatura seguem por parcela. Mudar o número de parcelas ou o total só vale no escopo "todas". Escopo que atinge parcela realizada exige `confirmar_realizadas`, com aviso de que muda o histórico de algo já realizado.
2. **Excluir o parcelamento** exige `confirmar_realizadas` (`DELETE /api/parcelamentos/{id}`). O aviso diz: "Isto apaga lançamentos já pagos e pode desconfigurar o histórico. Confirma?", e lista quantas parcelas serão apagadas de cada tipo (de fatura paga, realizadas de fatura aberta, editadas à mão). A tela só confirma depois de mostrar o aviso.

## Checklist

- [x] ~~API: parâmetro de escopo na edição, com os três valores, e `confirmar_realizadas` quando atinge realizadas~~ (parte 1 saiu, ticket 146)
- [x] API: `DELETE /api/parcelamentos/{id}` recusa sem `confirmar_realizadas` quando há realizadas ou editadas à mão, e devolve as contagens para o aviso
- [x] ~~Telas: seletor de escopo na edição~~ (parte 1 saiu, ticket 146)
- [x] Telas: aviso na exclusão, com o texto acima
- [x] Testes de API em `backend/tests/test_parcelamentos.py` (da exclusão)
- [x] ~~Verbetes "Parcela alterada à mão" e "Correção do parcelamento" do `GLOSSARY.md` atualizados~~ (parte 1 saiu, ticket 146)
- [x] Verificações do projeto rodando e PR aberto para `main` (da parte 2)

## Comments

- **2026-11-01, parte 2 feita.** Excluir o parcelamento responde 409 com `AvisoDeExclusao` (`parcelas`, `de_fatura_paga`, `realizadas`, `alteradas_a_mao`) quando alguma parcela é de fatura paga (a importada do Mobills também), realizada ou alterada à mão, e só apaga com `confirmar_realizadas=true`. As alteradas à mão também entram nas outras contas. A tela pergunta antes e, com o 409, mostra o aviso forte com as contagens; no cartão, a realizada fora da fatura paga aparece como "de fatura ainda não paga", porque também pode ser de fatura fechada sem pagamento.
- **Parte 1 parada.** O [ticket 136](136-alcance-da-mudanca-na-parcela.md) (PR #344, em paralelo) implementou o alcance na edição da parcela, em `PATCH /api/parcelas/{id}`, preservando a classificação alterada à mão, o oposto da Q7 do 99. O [ticket 146](146-escopo-na-parcela-e-a-classificacao-editada-a-mao.md) leva a escolha ao dono, inclusive se a parte 1 sai deste ticket. Uma versão da parte 1 sobre a correção do parcelamento (`alcance` e `parcela` no `PATCH /api/parcelamentos/{id}`, a classificação valendo para as alteradas à mão, confirmação quando atinge realizada) ficou na branch `rascunho/142-alcance-no-parcelamento`, só para consulta: ela duplica a API do 136 e não deve ser mesclada.
- **2026-11-07, fechado.** O dono decidiu no [ticket 146](146-escopo-na-parcela-e-a-classificacao-editada-a-mao.md) que a parte 1 sai daqui: o 136 já a fez, a classificação alterada à mão segue preservada e o número de parcelas e o total só mudam pela correção do parcelamento. A branch `rascunho/142-alcance-no-parcelamento` fica só como registro.
