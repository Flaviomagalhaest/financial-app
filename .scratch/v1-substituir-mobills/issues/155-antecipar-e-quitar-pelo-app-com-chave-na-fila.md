# Antecipar e quitar pelo app, com a chave na fila sem internet

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #377
Origem: [ticket 154](154-antecipacao-chave-de-idempotencia.md): o app ainda não chama `antecipar_parcelas` nem `quitar_parcelamento`, então o item "fila sem sinal envia a chave" do 154 não tinha onde ser feito

## O que construir

Antecipar (K parcelas) e quitar pela tela do parcelamento. A antecipação entra na fila sem internet como `criar_parcelamento` (46), com um id gerado no aparelho enviado como `id` (a chave do 154) para o reenvio não antecipar as K seguintes. A quitação não tem chave (o reenvio dá 422).

## Checklist

- [ ] Ação `antecipar_parcelas` na fila (`web/src/dados/fila.ts`, `armazem.ts`), com o id da antecipação
- [ ] Tela para antecipar/quitar, com data e valor total
- [ ] Teste e2e do reenvio
- [ ] Verificações do projeto e PR para `main`
