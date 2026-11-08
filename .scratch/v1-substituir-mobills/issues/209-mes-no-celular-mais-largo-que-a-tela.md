# Mês no celular fica mais largo que a tela e desloca a barra de baixo

Type: bug
Status: resolved
Blocked by: —
Skills: `tdd`, `implement`; apoio: `run`, `diagnosing-bugs` se a correção não bastar no aparelho
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #548
Origem: relato do dono (08/11), com capturas do app instalado no Android: na aba Mês a tela não fica posicionada (o botão "Adicionar item" sai pela direita, a barra de baixo aparece cortada embaixo e com a sexta aba cortada à direita); na Hoje fica certo.

## O que acontece

No cartão "Itens do planejamento", a fileira de novo item (`web/src/mes/TelaDoMes.tsx:237`, `<div className="linha">` com o `select` da categoria, o `input` do valor e o botão "Adicionar item") não quebra nem encolhe o bastante. O `.linha` (`web/src/estilo.css`, regra `.linha` e `.linha > input`) é `display: flex` sem `flex-wrap`, só o `input` encolhe (`min-width: 0`), e o `select` fica na largura do texto "Escolha a categoria". O resto passa da borda e a página inteira fica mais larga que a tela. Com a página mais larga, o navegador do Android desloca a área visível, e a barra de baixo (`.abas`, `position: fixed`) aparece cortada.

Reproduzido na sessão (triage, 08/11), com o `estilo.css` atual e só a fileira dentro do `main`, sem o recuo do cartão:

| Largura | Fonte | Largura da página | Campo do valor |
|---|---|---|---|
| 360 px | 100% | 381 px | 26 px |
| 393 px | 115% | 432 px | 30 px |
| 412 px | 130% | 482 px | 33 px |

A fonte maior (ajuste de fonte do Android, como no aparelho do dono) piora; o campo do valor quase some, como na captura. No app de verdade o recuo do cartão soma mais.

A mesma fileira (`select` + `input` + botão) aparece em `web/src/mes/TelaDoModelo.tsx:64`, `web/src/lancamentos/TelaDaRecorrencia.tsx` e `web/src/busca/FiltrosSalvos.tsx`; conferir as três.

## O que fazer

- A fileira de novo item cabe na tela no celular: categoria numa linha, valor e botão na outra (ou outra forma que caiba), sem o campo do valor sumir.
- Conferir as outras fileiras do mesmo tipo e corrigir as que estouram.
- Um teste e2e que abre cada aba (Hoje, Mês, Cartões, Histórico, Futuro) e o Modelo padrão a 360 px de largura e confere que a página não fica mais larga que a tela (`document.documentElement.scrollWidth <= innerWidth`), também com a fonte a 130%, para o estouro não voltar.

## Checklist

- [x] Teste e2e de largura vermelho no Mês antes da correção (`web/e2e/largura-no-celular.spec.ts`: 882 px numa tela de 360 px)
- [x] Fileira de novo item do Mês e do Modelo padrão cabendo a 360 px, com fonte 100% e 130%
- [x] Recorrência e Filtros salvos conferidos (a fileira "Última data" da recorrência e os dois formulários de filtros salvos passaram a quebrar; Filtros salvos entra no e2e)
- [x] Captura do Mês no celular antes e depois (a captura da tela do celular só mostra o topo; a fileira fica abaixo da dobra, então a prova é a medida de largura do e2e)
- [x] Specs e verificações do projeto verdes; PR para `main`
