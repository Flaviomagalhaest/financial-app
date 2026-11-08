# Lançamentos gerados por recorrência contam como usos do Sugerido?

Type: decision
Status: ready-for-human
Blocked by: —
Skills: `grilling`, `domain-modeling`; HITL (precisa do dono)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #556
Origem: [ticket 206](206-sugeridos-contam-parcelas-como-usos.md). O 206 passou a contar um parcelamento como um uso; as ocorrências de uma recorrência (ex.: aluguel mensal) ainda contam cada uma, então 5 meses de aluguel sugerem favoritar "Aluguel".

## Decisão

Uma regra de recorrência é uma escolha só da pessoa, como o parcelamento; mas o favorito serve para lançar com um toque, e o que a recorrência gera sozinha talvez nem precise dele. Decidir com o dono: contar a recorrência como um uso (como o parcelamento), contar cada ocorrência (hoje) ou não contar.

## Checklist

- [ ] Decisão do dono registrada aqui
- [ ] Se mudar, ajustar `_grupos` em `backend/app/favoritos.py` com teste, e o `GLOSSARY.md`
