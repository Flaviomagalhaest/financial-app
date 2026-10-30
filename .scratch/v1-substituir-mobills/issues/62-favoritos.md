# Favoritos

Type: task
Status: resolved
Blocked by: 42, 53
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #116
Origem: [spec da v1](../spec.md), etapa 6; histórias de usuário 30, 31, 32, 33, 34, 35, 36, 37

## O que construir

O casal lança o café de sempre com um toque. Fonte da interface: branch `prototipo/favoritos` (variante C); a tela de configurações dos favoritos não foi prototipada.

## Checklist

- [x] Fileira acima do teclado e grade na Hoje com a mesma lista; tocar preenche conta, categorias, tags, pessoa e o último valor (só padrão, editável, "Salvar" confirma)
- [x] Marcar pela ⭐ ou pelo "Favoritar" depois de salvar; grupo "Sugeridos" com os 3 mais repetidos a partir de 5 usos, promovíveis ou dispensáveis
- [x] Reordenar e remover nas configurações (só com internet); favoritos disponíveis offline pelo pacote para lançar
- [x] Testes de API e de navegador
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Tabela `favoritos` (migration 0049, backup na versão 18) e rotas `GET/POST /api/favoritos`, `DELETE /api/favoritos/{id}`, `PUT /api/favoritos/ordem` e `POST /api/favoritos/sugeridos/dispensar`; decisão do valor padrão na [ADR 0017](../../../docs/adr/0017-favorito-valor-padrao-derivado-do-ultimo-lancamento.md).
- App: fileira acima do teclado, grade e "Sugeridos" na Hoje, ⭐ e oferta "Favoritar", tela `#/favoritos` nas configurações.
- Escolhas provisórias e acabamentos: [ticket 107](107-favoritos-decisoes-e-acabamentos.md).
