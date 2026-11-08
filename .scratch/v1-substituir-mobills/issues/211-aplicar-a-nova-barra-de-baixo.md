# Aplicar a nova barra de baixo e a tela de funcionalidades no celular

Type: task
Status: ready-for-agent
Blocked by: 210
Skills: `implement`, `tdd`, `run`; apoio: `code-review`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #550
Origem: [ticket 210](210-barra-de-baixo-e-tela-de-funcionalidades.md), que decide o desenho com o dono. Este ticket aplica o que lá ficar aprovado; releia o `## Comments` do 210 antes de começar, porque ele pode mudar o escopo abaixo.

## O que construir

- No celular (abaixo de 900 px), a barra de baixo com Hoje, Mês, +, Cartões e o quinto item decidido no 210, equilibrada (duas posições de cada lado do +).
- A tela de funcionalidades aberta pelo quinto item, com Histórico e Futuro (e o que mais o 210 decidir), no padrão visual do [ticket 204](204-acabamento-visual-do-app.md), funcionando sem internet como as outras telas.
- Dentro de Histórico e Futuro, o quinto item marcado e o caminho de volta como o 210 decidir; `#/historico` e `#/futuro` continuam abrindo as telas.
- Na tela larga, nada muda: a barra lateral segue com Hoje, Mês, Cartões, Histórico e Futuro, e a tela de funcionalidades não aparece nela.

## Checklist

- [ ] `## Comments` do 210 relido; escopo deste ticket conferido com o que foi decidido
- [ ] Barra de baixo nova no celular e tela de funcionalidades
- [ ] Barra lateral da tela larga sem mudança (captura antes e depois)
- [ ] `web/e2e/pwa.spec.ts` e os testes que navegam pelas abas ajustados; teste novo para abrir Histórico e Futuro pela tela de funcionalidades
- [ ] Capturas do celular (claro e escuro) e da tela larga; specs e verificações do projeto verdes; PR para `main`
