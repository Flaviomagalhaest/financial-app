# Favoritos: decisões e acabamentos que sobraram do 62

Type: grilling
Status: ready-for-human
Blocked by: 62
Skills: `grilling` para o dono decidir; depois `implement`, `tdd`; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #220
Origem: [ticket 62](62-favoritos.md) (revisão e escolhas provisórias da implementação; ver também a [ADR 0017](../../../docs/adr/0017-favorito-valor-padrao-derivado-do-ultimo-lancamento.md))

## As perguntas

1. **Remover um favorito o dispensa**: ele não volta como sugerido, mesmo com 5 usos ou mais. A spec só diz "remover". Alternativa: voltar à lista de sugeridos.
2. **"Repetido" é a identidade inteira** (descrição, tipo, conta, categorias, tags e pessoa): o mesmo café com outra tag conta à parte. Alternativa: só descrição e conta.
3. **Os sugeridos aparecem na Hoje e nas configurações**, não na fileira do novo lançamento (a fileira traz só os favoritos).
4. **Reordenar por ↑/↓**, não por arrastar: a tela de configurações dos favoritos não foi prototipada.
5. **A oferta "Favoritar" some em 15 s** e só existe com internet.

## Acabamentos técnicos

- `identidadeDe` (web) usa `toLowerCase` e `identidade_de` (servidor) usa `casefold`: divergem em letras como "ß". Um teste de paridade com vetores comuns resolveria.
- Favorito com categoria juntada ou excluída pelo ticket de manutenção de categorias não é atualizado: o app só filtra as categorias que não existem mais.
- O pacote para lançar da spec é uma chamada só; hoje os favoritos são uma leitura própria (`GET /api/favoritos`), guardada no aparelho junto com o índice de sugestão.
- A falha intermitente de `web/e2e/lancamentos.spec.ts` ("cria, edita e exclui", `linha` ainda visível após a exclusão e o `reload`) apareceu uma vez na suíte inteira e passou isolada; não tem a ver com favoritos.

## Checklist

- [ ] O dono responde as perguntas e a resposta vai para `## Answer`
- [ ] Se uma regra mudar: teste em `backend/tests/test_favoritos.py` e ajuste em `backend/app/favoritos.py`
- [ ] Teste de paridade da identidade (servidor e app) e tratamento da categoria juntada
