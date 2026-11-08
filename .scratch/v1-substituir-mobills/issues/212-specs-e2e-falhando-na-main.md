# Seis specs e2e de parcelamento e recorrência falham na main

Type: bug
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`, `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #562
Origem: [ticket 211](211-aplicar-a-nova-barra-de-baixo.md): a suíte e2e completa (341 specs) falhou em seis, e as seis falham do mesmo jeito numa `main` limpa (`origin/main` em c5116dc), sem a mudança do 211. Rodadas em 08/11/2026.

## O que falha

- `estorno-de-parte-e-parcelas.spec.ts:77` (estorna todas as parcelas num estorno só)
- `janela-do-aparelho.spec.ts:220` (estorno de uma parcela na janela)
- `parcelamento.spec.ts:249` (muda uma parcela com alcance)
- `partes-na-compra-parcelada.spec.ts:77` (parcela que muda de valor se redivide)
- `recorrencia-mudar.spec.ts:278` e `:336` (recorrência descartada no meio do envio)

Sintomas vistos: o cabeçalho "Histórico" não aparece depois de lançar a compra parcelada ou a recorrência, e um `toHaveText("R$ 50,00")` do parcelamento erra o valor. Suspeita a conferir: dependência da data de hoje (08/11/2026) nos meses das parcelas, ou algo mudado depois do último verde da `main`.

## Checklist

- [ ] Causa achada (data, dado de teste ou regressão) e dita aqui
- [ ] As seis specs verdes na `main`
