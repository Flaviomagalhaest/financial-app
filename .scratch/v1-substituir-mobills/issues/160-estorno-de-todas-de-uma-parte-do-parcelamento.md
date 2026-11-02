# Estorno de todas as parcelas de uma parte do parcelamento

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #376
Origem: integração dos tickets [138](138-estorno-de-parte-e-de-todas-as-parcelas.md) e [139](139-partes-na-compra-parcelada.md): o 138 foi feito antes de o parcelamento ter partes, e o 139 não mexeu no estorno de todas

## O que construir

O 138 decidiu que "Todas as parcelas" cria um estorno só, ligado ao parcelamento **ou à parte dele**, e que na compra com partes a parte é obrigatória. Quando o 138 foi feito, o parcelamento não tinha partes, e `_conferir_estorno_de_todas` (`backend/app/lancamentos.py`) recusa `estorno_parte_id` com "o parcelamento ainda não tem partes". O 139 deu partes ao parcelamento (`parcelamento_partes`), e na integração dos dois ficou assim:

- o estorno de todas de um parcelamento com partes, **sem** parte, é aceito com as categorias do parcelamento, que é vazia: o crédito conta só no total da fatura e do mês, sem categoria, tag nem item;
- **com** parte, é recusado com "o parcelamento ainda não tem partes".

O estorno de uma parcela só, com a parte da parcela (`lancamento_partes`), já funciona.

## Checklist

- [x] No parcelamento com partes, o estorno de todas pede a parte (`estorno_parte_id` com o id de `parcelamento_partes`), herda as categorias, tags e item dela e vai até a soma dela nas parcelas menos o já estornado nela (de cada parcela e de todas)
- [x] Sem parte num parcelamento com partes, recusa como na compra com partes
- [x] O estorno acompanha a parte na correção do parcelamento e trava tirar a parte que tem estorno, como na compra à vista
- [x] A tela "Todas as parcelas" deixa escolher a parte, também sem internet
- [x] Testes de API e de navegador; verificações do projeto e PR para `main`

## Resposta

Feito na API e na tela:

- `_conferir_estorno_de_todas` pede a parte no parcelamento com partes ("o parcelamento tem partes: escolha a parte que foi estornada"). A parte precisa ser dele, e o estorno vai até a soma dela nas parcelas (`somas_nas_parcelas`) menos o já estornado nela. Isso conta o estorno de todas e o de cada parcela, na parte da parcela que veio dela (`id_na_parcela`). O estorno de uma parcela também respeita esse limite.
- `acompanhar_estornos_do_parcelamento` copia para o estorno de parte as categorias, as tags e a escolha de item da parte. Ele roda na correção do parcelamento.
- Na correção do parcelamento, a parte com estorno não sai, as partes não se juntam e a soma da parte não fica abaixo do estornado, como na compra à vista.
- A tela "Todas as parcelas" troca as partes da parcela pelas do parcelamento, com a soma de cada uma e o que ainda dá para estornar. Funciona sem internet, e a conta tem a tabela `tabelas-de-teste/somas-das-partes.json` (ADR 0018).
- ADR 0016 ganhou o adendo do 160.

Pendências no [ticket 161](161-limite-do-estorno-de-parte-do-parcelamento.md): soma pela regra ou pelas parcelas reais, item sem escolha explícita, ligação pela posição no aparelho.
