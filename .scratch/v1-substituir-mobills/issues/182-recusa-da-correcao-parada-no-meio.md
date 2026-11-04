# Recusa da correção parada no meio: a parcela em que parou e a tentativa de cada dia

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #448
Origem: revisão (Spec) do [ticket 180](180-fatura-paga-no-meio-do-refazer-da-correcao.md) (04/11)

## O que construir

A correção do parcelamento que uma fatura paga para no meio do refazer grava em `mudanca_recusada` o motivo de `cartoes.protegida` seguido de "A correção do parcelamento parou: as parcelas que faltavam corrigir ficaram como estavam" (ticket 180). Ficaram dois acertos:

- **A parcela em que parou.** A recusa da mudança com alcance diz "Da Nª parcela em diante" (`mudanca_na_parcela._desistir`, ticket 149); a da correção não diz. `_desistir_do_conserto` pode achar a primeira parcela que falta corrigir com `_correcoes`.
- **A tentativa de cada dia.** A correção recusada continua destoando do parcelamento, então `completar_todos` tenta de novo a cada dia (de propósito: se a fatura deixar de estar paga, o conserto termina e a recusa sai). Cada tentativa recusada regrava `mudanca_recusada` e, se havia nela a recusa de uma mudança com alcance, a troca pela da correção. Decidir se as duas convivem (dois campos ou o texto das duas) ou se a da correção, mais nova, basta.

## Checklist

- [ ] A recusa da correção diz a parcela a partir da qual as parcelas ficaram como estavam
- [ ] A tentativa diária não apaga a recusa de uma mudança com alcance sem o casal ver (ou fica registrado que basta a mais nova)
- [ ] Testes de API em `backend/tests/test_fatura_paga.py`
