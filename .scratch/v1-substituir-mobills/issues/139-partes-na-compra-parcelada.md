# Partes na compra parcelada

Type: task
Status: resolved
Blocked by: 136, 137
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Opus
Effort recomendado: high
Issue: #327
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

A compra parcelada pode ter partes, guardadas como proporção e aplicadas a cada parcela.

## Checklist

- [x] Cada parcela se divide pelas partes na proporção do total; os centavos vão para a maior parte (a primeira, no empate); o valor da parcela é o que vale
- [x] Parcela com valor editado à mão se redivide na mesma proporção
- [x] Mudar as partes numa parcela usa o alcance do ticket 136: "só esta" dá partes próprias à parcela; "esta e as próximas" e "todas" preservam as alteradas à mão
- [x] Correção do parcelamento redivide as parcelas pelas partes
- [x] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q27, Q33 a Q36 (revistas pela Q39) do ticket 94; ADR 0022.

## Answer

Feito na API, na correção, no backup e nas telas ([ADR 0022](../../../docs/adr/0022-partes-da-compra.md), consequência nova).

- **Modelo**: o parcelamento guarda as partes em `parcelamento_partes`, `parcelamento_parte_categorias` e `parcelamento_parte_tags`, com o valor de cada uma como proporção (migrations 0066 a 0069). Cada parcela recebe as partes divididas pelo valor dela (`app/partes.py`, `dividir`: a fatia sem os centavos, e os que sobram na maior parte, a primeira no empate), com o id vindo da parcela e da parte, e guarda a proporção em `lancamento_partes.proporcao` (0070; `proporcao_das_partes` na leitura), para a divisão seguinte não carregar o arredondamento. Backup na versão 28, com conversor da 27.
- **Criar**: `partes` no `POST /api/parcelamentos` (e no `criar_parcelamento` da fila) somam o valor digitado, o total ou o da parcela; o parcelamento com partes não tem categoria, tag, pessoa nem item; a menor parcela precisa dar um centavo a cada parte (422).
- **Valor editado à mão**: a parcela que muda de valor só nela (sem as partes, ou com elas só divididas pelo valor novo, como a tela manda), na confirmação ou na antecipação se divide de novo na proporção que tem, e fica alterada à mão só no valor.
- **Alcance**: as partes são um campo de classificação (`partes` em `CLASSIFICACAO`). "Só esta" dá partes próprias à parcela (alterada à mão em `partes`); "esta e as próximas" e "todas" levam a proporção ao parcelamento (dividir e juntar também) e preservam a parcela com partes próprias, contada em `parcelas_mantidas`. As partes, a categoria, as tags, a pessoa e o item mudam juntos ou ficam juntos, para a parcela nunca ter partes e classificação própria ao mesmo tempo. `PATCH /api/parcelamentos/{id}` também aceita `partes`.
- **Correção**: refaz cada parcela pela proporção do parcelamento (quando as partes são pedidas) ou pela que ela tem (quando só o valor muda), e confere antes de gravar que nenhuma parte fica sem um centavo. A tarefa diária termina a correção que parou no meio do mesmo jeito.
- **Edição em lote**: deixa de fora todas as parcelas de um parcelamento com partes, também a que uma pessoa juntou só nela (`com_partes_fora`), para o lote não levar categoria ao parcelamento.
- **Telas**: "Dividir em partes" vale no parcelado e na parcela; a parcela com partes intocadas acompanha o valor digitado na proporção guardada; o parcelado cuja menor parcela não dá um centavo a cada parte não salva; o aviso de planejamento divide a 1ª parcela pelas partes. A tela do parcelamento mostra as partes em percentual no lugar de categorias, tags e pessoa, e as partes de cada parcela.
- **Testes**: `backend/tests/test_partes_na_compra_parcelada.py` (16) e `web/e2e/partes-na-compra-parcelada.spec.ts` (3); backend inteiro e as specs de partes e de parcelamento verdes.

Pendências gravadas: [153](153-tarefa-diaria-para-no-conserto-recusado.md) (a tarefa diária para no parcelamento que um conserto recusa), [154](154-confirmar-compra-a-vista-com-partes-com-outro-valor.md) (decisão do dono: confirmar a compra à vista com partes com outro valor) e [155](155-mudar-as-partes-pela-tela-do-parcelamento.md) (decisão do dono: mudar as partes pela tela do parcelamento). O [151](151-correcao-de-fatura-com-compra-com-partes.md) continua para a compra à vista: a parcela com partes que muda de valor já se redivide.
