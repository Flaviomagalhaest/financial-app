# Escopo na edição de parcela e aviso forte ao excluir parcelamento

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`; apoio: `domain-modeling` para o `GLOSSARY.md`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #338
Origem: perguntas 7 e 8 do [ticket 99](99-parcelamento-regras-provisorias.md) (decisão do dono, `## Answer` do 99)

## O que construir

1. **Escopo na edição.** Editar uma parcela pergunta o escopo: **só esta**, **esta e as futuras** ou **todas (inclusive as realizadas)**. A descrição, as categorias, as tags, a pessoa e o item valem para as parcelas do escopo, inclusive as editadas à mão; valor, data, conta e fatura seguem por parcela. Mudar o número de parcelas ou o total só vale no escopo "todas". Escopo que atinge parcela realizada exige `confirmar_realizadas`, com aviso de que muda o histórico de algo já realizado.
2. **Excluir o parcelamento** exige `confirmar_realizadas` (`DELETE /api/parcelamentos/{id}`). O aviso diz: "Isto apaga lançamentos já pagos e pode desconfigurar o histórico. Confirma?", e lista quantas parcelas serão apagadas de cada tipo (de fatura paga, realizadas de fatura aberta, editadas à mão). A tela só confirma depois de mostrar o aviso.

## Checklist

- [ ] API: parâmetro de escopo na edição, com os três valores, e `confirmar_realizadas` quando atinge realizadas
- [ ] API: `DELETE /api/parcelamentos/{id}` recusa sem `confirmar_realizadas` quando há realizadas ou editadas à mão, e devolve as contagens para o aviso
- [ ] Telas: seletor de escopo na edição e aviso na exclusão, com o texto acima
- [ ] Testes de API em `backend/tests/test_parcelamentos.py`
- [ ] Verbetes "Parcela alterada à mão" e "Correção do parcelamento" do `GLOSSARY.md` atualizados
- [ ] Verificações do projeto rodando e PR aberto para `main`
