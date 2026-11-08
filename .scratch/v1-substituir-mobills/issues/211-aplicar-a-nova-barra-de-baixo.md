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

Decidido no 210 (detalhes no `## Comments` dele; protótipo aprovado, variante 4: https://claude.ai/artifact/EXim1PGPQL6HoLsLRVJppe, fonte na branch `prototipo/210-barra-de-baixo`, `.scratch/v1-substituir-mobills/prototipos/210/barra-de-baixo.html`):

- **Barra de baixo do celular** (abaixo de 900 px): Hoje, Mês, +, Cartões e o ícone de grade (Explorar), **todos só com ícone**, do mesmo tamanho (24 px), centralizados na altura da barra; o + segue como hoje. Os nomes viram `aria-label` ("Hoje", "Mês", "Novo lançamento", "Cartões", "Explorar"). O item marcado fica verde com uma pílula `--destaque-suave` atrás do ícone (claro e escuro). Ícone novo `grade` (quatro quadrados arredondados, 2×2) em `web/src/casca/icones.tsx`.
- **Tela Explorar** (`#/explorar`, título "Explorar", termo no `GLOSSARY.md`): seis cartões em grade de 2 colunas, só ícone e nome, nesta ordem: Histórico, Futuro, Busca, Favoritos, Contas e categorias, Configurações. Sem busca no alto. No padrão visual do [ticket 204](204-acabamento-visual-do-app.md), sem faixa, funcionando sem internet como as outras telas. Configurações precisa de um ícone novo (engrenagem).
- **Item marcado no celular**: Hoje, Mês e Cartões (com a fatura) marcam a si; as telas de lançar não marcam nada; toda outra tela marca a grade (Explorar, Histórico, Futuro, Busca, Edições em lote, Favoritos, Contas e categorias, Configurações), venha de onde vier. Tocar na grade volta à grade; nenhuma seta de voltar nova. O modelo do planejamento passa a marcar **Mês** (nas duas larguras); parcelamento, recorrência e conflito seguem sem marca.
- **Tela larga**: nada muda. A barra lateral segue com Hoje, Mês, Cartões, Histórico e Futuro, **com os nomes visíveis**; Busca e Edições em lote continuam marcando Histórico; as telas do Menu da conta seguem sem marca; não há item de Explorar na barra lateral. `#/explorar` aberto na tela larga mostra a grade, sem item marcado.
- **Sem mudança**: a lupa do topo, o Menu da conta e os endereços `#/historico` e `#/futuro`, que continuam abrindo as mesmas telas.

## Checklist

- [ ] `## Comments` do 210 relido; escopo deste ticket conferido com o que foi decidido
- [ ] Barra de baixo nova no celular (só ícones, pílula no marcado) e tela Explorar
- [ ] Barra lateral da tela larga sem mudança (captura antes e depois)
- [ ] `web/e2e/pwa.spec.ts` e os testes que navegam pelas abas ajustados (no celular, as abas são achadas pelo nome acessível, não pelo texto visível); teste novo para abrir Histórico e Futuro pela tela Explorar e para a marcação da grade
- [ ] Capturas do celular (claro e escuro) e da tela larga; specs e verificações do projeto verdes; PR para `main`
