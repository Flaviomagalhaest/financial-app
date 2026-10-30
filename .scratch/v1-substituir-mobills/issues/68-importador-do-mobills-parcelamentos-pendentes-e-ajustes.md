# Importador do Mobills: parcelamentos, pendentes e ajustes

Type: task
Status: claimed
Blocked by: 67, 47, 39
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #122
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 171, 172, 173, 174

## O que construir

O histórico importado já traz o futuro e as faturas certos, e o importador gera um backup válido que a restauração grava ([ADR 0008](../../../docs/adr/0008-ajuste-de-fatura-fica-na-fatura.md), [ADR 0012](../../../docs/adr/0012-exportacao-unica-zip-de-csvs-e-restauracao-so-em-banco-vazio.md)).

## Checklist

- [ ] Parcelas reagrupadas em parcelamentos, com as parcelas futuras que faltam geradas como previstas
- [ ] Pendentes que não são parcela: previstos avulsos se de meses seguintes ao export, descartados se do mês do export ou anteriores
- [ ] `Reajuste de fatura` vira ajuste de fatura; faturas importadas nascem com o mês da fatura do rótulo, fechadas e pagas, sem datas nem pagamento de fatura
- [ ] Saída é um backup válido; teste de que ele restaura num banco vazio
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Do [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md): O ajuste de fatura já tem onde ficar: `faturas.ajuste_centavos` (migration `0038`, backup na versão 14), editável por `PATCH /api/cartoes/{id}/faturas/{mes}`; o `Reajuste de fatura` importado grava ali.
- Do [ticket 46](46-parcelamento-criar.md): o backup (versão 16) traz `parcelamentos` (sem coluna de tipo; `valor_total_centavos`, `parcelas`, `data` da compra ou da 1ª parcela, `automatico`, `geradas`), `parcelamento_categorias`, `parcelamento_tags` e, em `lancamentos`, `parcelamento_id` e `parcela`. Para a tarefa diária não gerar de novo, `geradas` = `parcelas`, e o id da parcela gerada pelo importador deve ser `uuid5(parcelamento, número)`, como o do app. No cartão, o parcelamento é sempre automático.
