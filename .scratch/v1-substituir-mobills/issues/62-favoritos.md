# Favoritos

Type: task
Status: ready-for-agent
Blocked by: 42, 53
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #116
Origem: [spec da v1](../spec.md), etapa 6; histórias de usuário 30, 31, 32, 33, 34, 35, 36, 37

## O que construir

O casal lança o café de sempre com um toque. Fonte da interface: branch `prototipo/favoritos` (variante C); a tela de configurações dos favoritos não foi prototipada.

## Checklist

- [ ] Fileira acima do teclado e grade na Hoje com a mesma lista; tocar preenche conta, categorias, tags, pessoa e o último valor (só padrão, editável, "Salvar" confirma)
- [ ] Marcar pela ⭐ ou pelo "Favoritar" depois de salvar; grupo "Sugeridos" com os 3 mais repetidos a partir de 5 usos, promovíveis ou dispensáveis
- [ ] Reordenar e remover nas configurações (só com internet); favoritos disponíveis offline pelo pacote para lançar
- [ ] Testes de API e de navegador
- [ ] Verificações do projeto rodando e PR aberto para `main`
