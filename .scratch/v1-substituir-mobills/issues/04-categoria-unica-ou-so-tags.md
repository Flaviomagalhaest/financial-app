# Categoria única ou só tags

Type: grilling
Status: ready-for-human
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add2e6d50ea91b1cf63692c
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Além das tags, cada lançamento tem uma classificação exclusiva (uma categoria, com ou sem subcategoria)?

O dono quer várias tags num mesmo lançamento ("família" e "alimentação" ao mesmo tempo), e o planejamento fala em "R$ 1.000 em alimentação". Decidir:

- sobre o que o planejamento incide: tags, uma categoria exclusiva ou os dois;
- como gráficos de proporção (pizza) e totais somam quando um lançamento tem várias tags, sem passar de 100%;
- se as tags têm grupos ou hierarquia;
- como as categorias e subcategorias do Mobills entram aqui (viram tags? viram categorias?), usando o achado de [O que o Mobills exporta](01-o-que-o-mobills-exporta.md).

## Checklist

- [ ] Decisão registrada em `## Answer`
- [ ] `GLOSSARY.md` atualizado com os termos resolvidos
- [ ] ADR em `docs/adr/` se a decisão for difícil de reverter, surpreendente e fruto de um trade-off real

## Comments

- Com o [ticket 01](01-o-que-o-mobills-exporta.md) resolvido: o Mobills exporta uma `Categoria` por lançamento, `Subcategoria` vazia em todas as linhas de teste e `Tags` como texto livre (uma por linha nas amostras: `novo ap`, `ilhabela`, `viagem`). Na amostra, 18 a 25 categorias por período e 3 tags no total. Ou seja, o histórico chega com categoria exclusiva e quase sem tags.
