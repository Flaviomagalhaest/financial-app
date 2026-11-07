# Busca: cartão titular e compras do adicional (open banking)

Type: task
Status: needs-triage
Blocked by: nenhum
Skills: `triage`; depois `grilling` e `implement`, `tdd` quando houver integração open banking
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #407
Origem: [ticket 111](111-busca-regras-provisorias.md), pergunta 7: na entrada manual não existe cartão adicional, então o filtro "Conta ou cartão" não traz as compras do adicional ao filtrar pelo titular. O dono lembrou que, com open banking, compras de cartão adicional podem chegar.

## O que construir

Quando a integração open banking for planejada, decidir se o filtro "Conta ou cartão" do titular passa a incluir as compras dos adicionais (hoje só o filtro Fatura as traz).

## Checklist

- [ ] Reavaliar quando existir ticket de integração open banking
- [ ] Se mudar a regra: teste em `backend/tests/test_busca.py`, ajuste em `backend/app/busca.py` e `web/src/dados/busca.ts`, README (seção Busca)

## Triagem (2026-11-07)

- Redundância: `backend/app/busca.py` e `web/src/dados/busca.ts` não têm regra de cartão adicional, e não existe ticket, ADR nem glossário de open banking. Nada a implementar agora.
- Recomendação: categoria `enhancement`, estado `needs-triage` (adiado). Reavaliar quando o primeiro ticket de integração open banking for criado; até lá o ticket fica parado.
