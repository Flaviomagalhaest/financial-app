# Favoritos: categoria juntada e pacote único para lançar

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #388
Origem: [ticket 108](108-favoritos-decisoes-e-acabamentos.md)

- Favorito com categoria juntada ou excluída pela manutenção de categorias não é atualizado: o app só filtra as que não existem mais. Atualizar o favorito (ou remapear a categoria juntada).
- O pacote para lançar da spec é uma chamada só; hoje os favoritos são `GET /api/favoritos`, guardado no aparelho junto com o índice de sugestão.

## Checklist

- [ ] Teste e ajuste para a categoria juntada/excluída
- [ ] Decidir e, se couber, unificar o pacote para lançar
