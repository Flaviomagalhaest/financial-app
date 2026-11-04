# Favoritos: categoria juntada e pacote único para lançar

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #388
Origem: [ticket 108](108-favoritos-decisoes-e-acabamentos.md)

- Favorito com categoria juntada ou excluída pela manutenção de categorias não é atualizado: o app só filtra as que não existem mais. Atualizar o favorito (ou remapear a categoria juntada).
- O pacote para lançar da spec é uma chamada só; hoje os favoritos são `GET /api/favoritos`, guardado no aparelho junto com o índice de sugestão.

## Checklist

- [x] Teste e ajuste para a categoria juntada/excluída
- [x] Decidir e, se couber, unificar o pacote para lançar: não unificado (ver `## Answer`)

## Answer

- **Categoria juntada**: `juntar_categoria` passa a remapear os favoritos (e os dispensados) para o destino, inclusive nas partes, e refaz a identidade (`juntar_categoria_nos_favoritos`, `backend/app/favoritos.py`). Se o remapeamento deixar dois favoritos iguais, fica o que já existia com a identidade. O valor padrão continua, porque a identidade dos lançamentos também foi remapeada pela junção.
- **Categoria excluída**: `excluir_categoria` recusa com 409 ("categoria em favorito"), como já recusa com lançamentos, transferências e planejamento: o dono arquiva ou junta.
- **Pacote único**: não unificado. O [ticket 63](63-sugestao-pelo-historico.md) já registrou que o pacote para lançar é feito de leituras guardadas uma a uma na camada de dados (ticket 33); `GET /api/favoritos` já devolve favoritos e sugeridos numa chamada só. Unificar tudo num endpoint exigiria reescrever a camada de dados do aparelho sem ganho funcional; nenhuma regra mudou.
