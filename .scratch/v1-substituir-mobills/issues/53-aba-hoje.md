# Aba Hoje

Type: task
Status: ready-for-agent
Blocked by: 43, 51, 33
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #107
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 120, 121, 30, 31

## O que construir

Ao abrir o app o casal vê o essencial, e os favoritos entram aqui no ticket de favoritos.

## Checklist

- [ ] Uma leitura para a tela Hoje: "ainda dá para gastar" em destaque, lista "a escolher", atrasados, fatura que vence e itens acima de 80%
- [ ] Avisos de não enviados e de conflitos; contas da semana
- [ ] Última resposta em cache com "atualizado às" sem internet
- [ ] Testes de API e de navegador; fonte da interface: branch `prototipo/dashboards`
- [ ] Verificações do projeto rodando e PR aberto para `main`
- [ ] O bloco `ContasDaSemana` (ticket 43, `web/src/lancamentos/ContasDaSemana.tsx`) já está na Hoje com a leitura própria `GET /api/contas-da-semana`: juntá-lo à leitura única da tela, e mostrar os atrasados pelo campo `atrasado` do lançamento
