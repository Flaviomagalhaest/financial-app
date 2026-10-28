# PWA instalável e casca das telas

Type: task
Status: resolved
Blocked by: 30
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #85
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 1, 2, 3, 23, 24

## O que construir

O app instala na Tela de Início do iPhone e do Android e abre no computador com layout de tela larga, já com a navegação por abas vazia.

## Checklist

- [x] Manifesto da PWA com ícones, nome, `display` standalone e o atalho "Novo lançamento" (`shortcuts`) que no Android aparece no toque longo do ícone
- [x] Service worker que guarda a casca do app para abrir sem internet
- [x] Navegação com as abas Hoje, Mês, Cartões, Histórico e Futuro (vazias) e botão "+ Novo lançamento" na tela inicial, em layout de celular e de tela larga na mesma base
- [x] Teste de navegador conferindo manifesto, abertura offline da casca e os dois layouts
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Rota no hash (`/#/hoje`, `/#/novo`): o endereço nunca muda e o CloudFront não precisa de regra de SPA. O atalho do manifesto aponta para `/#/novo`, que hoje é uma tela de aviso até o ticket 32.
- Service worker escrito à mão (`web/service-worker.js`), com a lista da casca gerada no build por um plugin do `vite.config.ts`; sem dependência nova. Rede primeiro na navegação, cache primeiro nos arquivos, `/api` fora.
- Ícones provisórios: [ticket 73](73-icone-definitivo-do-app.md).
