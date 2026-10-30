# Aba Hoje

Type: task
Status: resolved
Blocked by: 43, 51, 33
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #107
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 120, 121, 30, 31

## O que construir

Ao abrir o app o casal vê o essencial, e os favoritos entram aqui no ticket de favoritos.

## Checklist

- [x] Uma leitura para a tela Hoje: "ainda dá para gastar" em destaque, lista "a escolher", atrasados, fatura que vence e itens acima de 80%
- [x] Avisos de não enviados e de conflitos; contas da semana
- [x] Última resposta em cache com "atualizado às" sem internet
- [x] Testes de API e de navegador; fonte da interface: branch `prototipo/dashboards`
- [x] Verificações do projeto rodando e PR aberto para `main`
- [x] O bloco `ContasDaSemana` (ticket 43, `web/src/lancamentos/ContasDaSemana.tsx`) já está na Hoje com a leitura própria `GET /api/contas-da-semana`: juntá-lo à leitura única da tela, e mostrar os atrasados pelo campo `atrasado` do lançamento

## Notas

- Do [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md): `ainda_da_para_gastar_centavos` do planejamento já desconta os ajustes de fatura do mês (`ajustes_de_fatura_centavos`, ADR 0008) e os itens contam o estorno com sinal contrário; a leitura da tela lê isso, sem recalcular.
- Do [ticket 51](51-item-do-lancamento-e-a-escolher.md): a lista "a escolher" sai pronta de `GET /api/planejamento/{mes}` (`a_escolher`: `lancamento_id`, `item_categoria_id` com o item em que ele conta enquanto ninguém escolhe, e `categorias_com_item`). Escolher é `PATCH /api/lancamentos/{id}` com `item_categoria_id`, que também vai pela fila (`CAMPOS` em `web/src/dados/fila.ts`).
