# Importador do Mobills: parcela com outro valor ou sem `(n/total)` continua a sequência

Type: task
Status: resolved
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

- [x] Teste: parcela no meio com outro valor continua a sequência (não vira duas)
- [x] Teste: duas sequências paralelas iguais com valores diferentes continuam separadas pelo valor
- [x] Teste: linha sem sufixo no mês do buraco vira a parcela, com o número deduzido; sem sufixo e com outro valor continua avulsa
- [x] Decidir com o dono (HITL): a parcela gerada para uma sequência aceita como `parcelamento` que acaba antes do último mês cai como prevista em mês já exportado (ticket 216); entra realizada?
- [x] Rodar de novo nos exports reais e gravar a nova contagem de `Parcelas quebradas` (esperado: bem menos que 342)

## Answer

Grilling curto com o dono em 2026-11-08.

### Decisões

- **Parcela gerada em mês já exportado (checklist)**: a sequência aceita como `parcelamento` que acaba antes do último mês gera as parcelas que faltam **realizadas até o último mês pago** (o último mês com lançamento pago no geral: o banco cobrou) e previstas depois.
- **Compras iguais em paralelo (pergunta nova)**: "duas parcelas no mês" só quando as duas têm o mesmo valor (±1 centavo). Com outro valor são duas compras: viram dois parcelamentos sem passar pela revisão. Nos exports reais eram 12 das linhas que sobravam (ex.: 70,53 e 112,48, as duas `1 a 3 de 3`).

### O que foi feito (`backend/app/mobills/parcelas.py`, `importacao.py`)

- O valor deixou de ser condição para continuar a sequência: desempata as compras paralelas, primeiro pelo valor mais perto e depois pelo mesmo cartão.
- A linha sem `(n/total)` com a mesma descrição, o valor de uma parcela vizinha (±1 centavo) e o mês exato do buraco vira a parcela, com o número deduzido. O buraco pode estar no meio (e então junta os dois pedaços, escolhendo o de valor mais perto quando há compras paralelas), no fim ou antes da 1ª parcela que veio. A linha deixa de ser avulsa: no backup, ela entra como parcela do parcelamento.
- `descartar duplicada` só tira a parcela que tem outra de mesmo valor no mês, para não apagar a compra paralela de outro valor.
- A parcela gerada até o último mês pago entra realizada. Isso mudou o teste do ticket 216, que esperava prevista a parcela de 2019-05 com o mês pago em 2019-06.

### Nos exports reais

`Parcelas quebradas`: **340 → 49** (a `main` dava 340 nesta rodada; o ticket 216 contou 342). Nenhuma sobra por parcela repetida, 18 têm cartão; 13 só faltam no fim, 13 só no começo, 23 nos dois. Foram 249 linhas sem sufixo deduzidas como parcela. O total de lançamentos foi de 6.349 para 6.413, porque mais sequências chegam ao último mês e geram as parcelas futuras. As 49 que sobram são os casos que o ticket 216 já esperava (outra descrição, mês fora da sequência, parcela que não está no export) e passam pela coluna de decisão da aba.

### Limites conhecidos (aceitos)

- A linha sem sufixo deduzida mantém a situação do Mobills, como qualquer parcela `(n/total)`. Uma `Pendente` num mês já pago entraria prevista. Nos exports reais isso não acontece (0 das 249).
- A suíte que precisa do Postgres (backup do importador) não rodou na máquina da sessão; roda no CI do PR.
