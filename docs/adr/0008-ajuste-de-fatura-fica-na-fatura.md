---
status: accepted
---

# Ajuste de fatura fica na fatura, fora das categorias

Com o lançamento manual, a soma das compras de uma fatura às vezes não bate com o valor real dela (uma compra esquecida ou lançada errada); no Mobills, o casal acertava a diferença com linhas de `Reajuste de fatura`. Aqui a diferença é o **ajuste de fatura**: um valor guardado na própria fatura, e não um lançamento. Ele conta no total da fatura, nas despesas do mês, no "quanto ainda posso gastar" e no fechamento do mês, mas não conta em categoria, tag nem item do planejamento, porque não se sabe o que foi comprado. Vale para a importação (cada `Reajuste de fatura` vira o ajuste da fatura dele) e para o uso depois da virada.

## Considered Options

- **Lançamento com a categoria "Ajuste"**: entraria nas estatísticas por categoria e no planejamento como se fosse um gasto de um tipo conhecido, e "Ajuste" viraria uma categoria que ninguém planeja.
- **Descartar as diferenças**: o total do mês ficaria abaixo do que saiu de fato.
