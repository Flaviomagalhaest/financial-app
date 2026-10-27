# PWA instalável e casca das telas

Type: task
Status: ready-for-agent
Blocked by: 30
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #85
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 1, 2, 3, 23, 24

## O que construir

O app instala na Tela de Início do iPhone e do Android e abre no computador com layout de tela larga, já com a navegação por abas vazia.

## Checklist

- [ ] Manifesto da PWA com ícones, nome, `display` standalone e o atalho "Novo lançamento" (`shortcuts`) que no Android aparece no toque longo do ícone
- [ ] Service worker que guarda a casca do app para abrir sem internet
- [ ] Navegação com as abas Hoje, Mês, Cartões, Histórico e Futuro (vazias) e botão "+ Novo lançamento" na tela inicial, em layout de celular e de tela larga na mesma base
- [ ] Teste de navegador conferindo manifesto, abertura offline da casca e os dois layouts
- [ ] Verificações do projeto rodando e PR aberto para `main`
