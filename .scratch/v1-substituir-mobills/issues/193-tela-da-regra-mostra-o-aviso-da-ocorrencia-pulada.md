# Tela da regra mostra e dispensa o aviso da ocorrência pulada

Type: task
Status: resolved
Blocked by: 192
Skills: `implement`, `tdd`, `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #483
Origem: decisão do [ticket 184](184-aviso-da-ocorrencia-que-a-fatura-paga-tirou.md)

## O que fazer

A tela da recorrência mostra o aviso que o ticket 192 grava (como a tela do parcelamento mostra a recusa travada), com o botão para o casal dispensar ("Entendi"), que chama o endpoint de dispensa. Só na tela da regra: não entra nos avisos da aba inicial.

Contrato do 192: a regra lida (`GET /api/recorrencias`) traz `aviso_da_fatura_paga` (texto pronto, ou `null`), e a dispensa é `DELETE /api/recorrencias/{id}/aviso-da-fatura-paga` (204).

## Checklist

- [x] Teste da tela: com aviso aparece; sem aviso não; dispensar some e chama o endpoint
- [x] Mostrar o aviso e o botão na tela da regra
- [x] Ver funcionando no app (`run`)
