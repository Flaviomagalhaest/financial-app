---
status: accepted
---

# O valor padrão do favorito vem do último lançamento com a mesma identidade

O favorito guarda conta, categorias, tags, pessoa e um valor inicial, mas o valor que o app mostra é o do último lançamento com a mesma **identidade** (descrição normalizada, tipo, conta, categorias, tags e pessoa), calculado na leitura, no servidor e, por cima, no aparelho com a fila. Os usos que fazem um lançamento virar **sugerido** contam pela mesma identidade. Nenhum lançamento aponta para o favorito, e nada é gravado a cada uso.

## Considered Options

- **Gravar o último valor no favorito a cada uso**: sem internet, o uso mora na fila, e o favorito só muda com internet (ADR 0011); o valor ficaria velho ou exigiria uma mudança de favorito na fila.
- **Coluna `favorito_id` no lançamento**: mexe no lote da fila, no backup e na planilha por um dado que a identidade já dá.

## Consequences

- Mudar categorias, tags ou conta antes de salvar faz o lançamento sair da identidade do favorito: o valor padrão não acompanha esse lançamento.
- Remover um favorito o guarda como "dispensado" (mesma tabela, `estado`), para não voltar como sugerido; favoritar de novo o traz de volta.
- `categoria_ids` e `tags` ficam como texto JSON na linha: o DSQL não tem coluna de lista (ADR 0009). O backup sobe para a versão 18.
- A identidade existe em dois lugares que precisam coincidir: `identidade_de` (`backend/app/favoritos.py`) e `identidadeDe` (`web/src/dados/favoritos.ts`).
