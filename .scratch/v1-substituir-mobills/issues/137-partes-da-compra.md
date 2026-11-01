# Partes da compra à vista

Type: task
Status: resolved
Blocked by: 133
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Opus
Effort recomendado: high
Issue: #325
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

Uma despesa à vista, no cartão ou na conta, pode ser dividida em partes, cada uma com descrição, valor, categorias, tags, pessoa e item próprios ([ADR 0022](../../../docs/adr/0022-partes-da-compra.md)).

## Checklist

- [x] Modelo e migração: partes ligadas ao lançamento; versão nova do backup
- [x] API: criar e editar compra com 2 partes ou mais, soma igual ao valor (senão 422); tirar a penúltima parte devolve os dados dela à compra
- [x] A compra com partes não tem categoria, tag nem pessoa próprias
- [x] Somas: categoria, tag, pessoa e item do planejamento leem as partes; fatura, mês e saldo leem a compra
- [x] Telas: dividir em partes no lançamento; a compra aparece numa linha só na fatura e no extrato e abre as partes; o filtro por categoria, tag ou pessoa mostra só a parte que bate, com o valor dela
- [x] Aviso de planejamento na tela de lançar: uma linha por parte
- [x] Planilha: uma linha por parte ("<compra> — <parte>")
- [x] Fila sem internet: a compra com partes é um pedido só; no conflito, as partes são um campo só
- [x] A importação do Mobills não cria partes
- [x] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q16, Q17, Q27 a Q29, Q31, Q32, Q44 e Q46 do ticket 94.

## Answer

Feito na API, nas somas, na planilha, no backup e nas telas.

- **Modelo**: `lancamento_partes`, `parte_categorias` e `parte_tags` (migrations 0060 a 0063); o lançamento traz `partes` (id do aparelho, descrição, valor, categorias, tags, pessoa e item). Backup na versão 25 do formato, com conversor da 24.
- **API**: criar e editar com duas partes ou mais, somando o valor (senão 422), só na despesa à vista; a compra com partes não tem categoria, tag, pessoa nem item próprios. No `PATCH`, `partes` com uma só (ou vazia, com as categorias) junta: a compra volta a ser uma com a classificação da parte que ficou; o valor continua o da compra, e a descrição também (na tela, a compra sem descrição fica com a da parte). As partes são um campo só no conflito, e dividir também conta como mudança de categorias, tags, pessoa e item. Parcela, previsto da recorrência e estorno ainda não têm partes (139, 140, 138): a API recusa. Juntar e excluir categoria ou tag levam as das partes.
- **Somas** (`app/partes.py`): totais e ranking do mês, histórico por categoria, itens do planejamento e "a escolher" (com `parte_id`) leem as partes; fatura, mês e saldo leem a compra. O ranking traz `parte_ids`; a busca, `partes_achadas` e o valor das partes que batem, e acha a compra pela descrição de uma parte.
- **Telas**: "Dividir em partes" na tela de lançar (a última parte fica com o que falta da compra; tirar a penúltima junta); aviso de planejamento por parte; a compra numa linha só no Histórico, na fatura, na busca e na folha do ranking, que abre as partes; com filtro, só a parte que bate, com o valor dela; "a escolher" da Hoje por parte; "Partes" na tela de conflito; a busca sem internet segue a mesma regra.
- **Planilha**: uma linha por parte, "<compra> — <parte>". A importação do Mobills não cria partes (teste no importador).
- A sugestão e o favorito deixam a compra com partes de fora até o 141, e a edição em lote também (`com_partes_fora`).
- De passagem: o `estilo.css` tinha o bloco `.evolucao` sem fechar, e o que vinha depois dele (busca, edição em lote, medidor) só valia dentro da aba Histórico; foi fechado.

Pendências gravadas: [150](150-edicao-em-lote-na-compra-com-partes.md) (edição em lote na compra com partes, decisão do dono) e [151](151-correcao-de-fatura-com-compra-com-partes.md) (correção de fatura que muda o valor de uma compra com partes).
