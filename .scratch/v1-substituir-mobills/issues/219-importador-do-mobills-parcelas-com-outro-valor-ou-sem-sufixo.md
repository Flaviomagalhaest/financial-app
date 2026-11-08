# Importador do Mobills: parcela com outro valor ou sem `(n/total)` continua a sequência

Type: task
Status: claimed
Blocked by: —
Skills: `tdd`, `implement`; `grilling` curto para a parcela gerada em mês já exportado (HITL: decisão do dono); `run` para rodar de novo nos exports reais (os exports ficam na máquina do dono, em `data/historic/`)
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #569
Origem: [ticket 216](216-importador-do-mobills-decisao-para-grupos-ambiguos-e-parcelas-quebradas.md) (diagnóstico dos 342 parcelamentos quebrados nos exports reais: a maior parte é defeito do reagrupamento em `backend/app/mobills/parcelas.py`, não dado faltando)

## O que construir

Hoje `reagrupar` só continua uma sequência quando a parcela seguinte tem a mesma descrição, o mesmo total, o número seguinte, o mês seguinte **e o valor da 1ª parcela com 1 centavo de tolerância**, e só olha linhas com `(n/total)`. Nos exports reais isso parte compras de verdade em duas sequências. Contando cada parcela que falta (começo e fim) uma vez:

- **234** são parcelas que existem no mês certo com valor diferente da 1ª em mais de 1 centavo (117 compras partidas; 35 diferem até 10 centavos, 71 até 10%, 11 mais; 103 no meio da sequência, 14 na última);
- **168** são parcelas que estão no geral no mês certo e com o valor da sequência, mas **sem o sufixo `(n/total)`** (ex.: "Televisão" é `(12/21)` em 2024-08, só "Televisão" em 2024-09 e `(14/21)` em 2024-10); quase todas do Personnalite (42 em 2026-03, 25 em 2024-09, 19 em 2024-11). O PDF do banco confirma que foram cobradas (Televisão 13/21, Sofá 8/10, Robo aspirador 9/10, com o valor exato);
- 12 estão sem sufixo e com outro valor; 24 não estão no export.

Decisões do dono (grilling do ticket 216, Q4 e Q12):

1. Mesma descrição, mesmo total, número seguinte e mês seguinte com outro valor **é a mesma compra**: o valor deixa de ser condição para continuar a sequência e serve só para desempatar sequências paralelas (escolher a de valor mais perto, depois a do mesmo cartão).
2. Uma linha **sem `(n/total)`** com a mesma descrição, o valor da sequência (±1 centavo) e o mês exato do buraco **é a parcela que falta**; o número é deduzido pela posição. Ela deixa de ser avulsa.

## Checklist

- [ ] Teste: parcela no meio com outro valor continua a sequência (não vira duas)
- [ ] Teste: duas sequências paralelas iguais com valores diferentes continuam separadas pelo valor
- [ ] Teste: linha sem sufixo no mês do buraco vira a parcela, com o número deduzido; sem sufixo e com outro valor continua avulsa
- [ ] Decidir com o dono (HITL): a parcela gerada para uma sequência aceita como `parcelamento` que acaba antes do último mês cai como prevista em mês já exportado (ticket 216); entra realizada?
- [ ] Rodar de novo nos exports reais e gravar a nova contagem de `Parcelas quebradas` (esperado: bem menos que 342)
