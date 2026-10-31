# Busca

Type: task
Status: resolved
Blocked by: 54, 55
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #113
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 137, 138, 139, 140, 141, 142, 143, 144, 145

## O que construir

O casal acha qualquer lançamento desde 2019 pela lupa, de qualquer aba ([ADR 0013](../../../docs/adr/0013-busca-por-data-da-compra-e-fatura-a-parte.md), [ticket 24](24-busca-e-filtros-salvos.md)).

## Checklist

- [x] Texto livre e filtros combinados; período pela data da compra e filtro Fatura à parte; linha fixa explicando a diferença para a aba Mês
- [x] Compra parcelada numa linha que abre as parcelas (cada parcela uma linha com o filtro Fatura); totais no topo com previstos à parte e transferências fora; ordenação e paginação sem teto
- [x] Atalhos "ver os lançamentos" do Mês e dos Cartões abrem a busca filtrada
- [x] Sem internet, resultado parcial do que o aparelho guarda, com aviso
- [x] Testes de API e de navegador
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas da implementação

- **API**: `POST /api/busca` (`backend/app/busca.py`, testes em `backend/tests/test_busca.py`) recebe os critérios, a ordem e a página e devolve as linhas da página, `tem_mais` e os totais do resultado inteiro. Texto livre na descrição sem acento nem maiúscula (o curinga do LIKE é escapado); filtros de valor, categorias e "sem categoria", tags e "sem tag", conta ou cartão (`conta_ids`), pessoa e "Conjunto", período (pela data da compra; no boleto parcelado, a da 1ª parcela), Fatura (cartão com os adicionais e mês; sem cartão, o mês em que cada lançamento conta), situação e tipo. Fora do filtro Fatura, o parcelamento é uma linha (`parcelamento`, com as parcelas achadas, cada uma com a fatura e a situação); no filtro, cada parcela é uma linha. As transferências (ADR 0014) vêm numa linha própria, fora dos totais e da contagem; o pagamento de fatura só com o tipo transferência. Totais: quantidade, despesas (o estorno diminui), receitas e saldo, com o previsto à parte. Linhas por página em `buscaPorPagina` (`config/valores-iniciais.json`). `transferencias.ler_por_ids` é função pública nova.
- **Tela** (`web/src/busca/`, rota `#/busca?<critérios>`): a lupa no topo abre a busca de qualquer aba e marca a aba Histórico. O texto busca 300 ms depois de parar de digitar; os filtros ficam numa folha e aparecem como fichas que se tiram com um toque; ordem "Mais recentes" ou "Maior valor"; a linha fixa sobre o período some no filtro Fatura; totais no topo, com os previstos e o saldo previsto à parte; "Carregar mais" pede a página seguinte. Os critérios ficam no endereço (`enderecoDaBusca`/`criteriosDoEndereco` em `web/src/dados/busca.ts`).
- **Atalhos**: a folha do ranking do Mês abre a busca das despesas da linha no mês em que contam (filtro Fatura sem cartão, mais a categoria, a tag ou a pessoa); o detalhe da fatura abre o filtro Fatura do cartão, com a categoria e a tag escolhidas lá.
- **Sem internet**: `useBusca` (`web/src/dados/index.ts`) cai na busca do aparelho (`buscarNoAparelho`), com as mesmas regras sobre a lista guardada e a fila por cima, sem as transferências, e a tela avisa "Resultado parcial, sem internet". Quando a rede volta ou a fila sobe, a busca roda de novo no servidor.
- **Testes de navegador** em `web/e2e/busca.spec.ts`: lupa, texto, filtros, fichas, ordem, parcelamento que abre, totais, endereço que sobrevive ao recarregar, os dois atalhos e o resultado parcial com um lançamento não enviado.
- **Fora do ticket, mas necessário**: `web/src/estilo.css` tinha uma `}` faltando em `.modelo-do-planejamento > label select` (sobra de merge); com o aninhamento de CSS do navegador, todas as regras depois dela (Hoje, favoritos, Futuro, tabelas e as da busca) ficavam presas dentro daquele seletor.
- **Vocabulário**: **Busca** e **Filtro Fatura** no `GLOSSARY.md`. O código usa "parcelamento", não "compra parcelada" (termo evitado no glossário, embora o ADR 0013 o use).
- **Pendências**: as regras provisórias (filtro Fatura sem cartão, parcelamento com filtro de situação, realizado e previsto nos totais, atalho do Mês, estorno no filtro de valor, transferências, conta e cartão num filtro só, ajuste de fatura, valores iniciais, sem internet e a lupa) vão para o dono no [ticket 111](111-busca-regras-provisorias.md); medir a busca com o histórico desde 2019 e decidir o índice fica no [ticket 112](112-busca-desempenho-e-indice.md). A reserva do ticket (`reserva-59`) não foi feita: a sessão trabalhou direto na branch que o ambiente designou.
