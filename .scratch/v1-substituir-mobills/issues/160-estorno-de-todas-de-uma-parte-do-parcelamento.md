# Estorno de todas as parcelas de uma parte do parcelamento

Type: task
Status: ready-for-agent
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

- [ ] No parcelamento com partes, o estorno de todas pede a parte (`estorno_parte_id` com o id de `parcelamento_partes`), herda as categorias, tags e item dela e vai até a soma dela nas parcelas menos o já estornado nela (de cada parcela e de todas)
- [ ] Sem parte num parcelamento com partes, recusa como na compra com partes
- [ ] O estorno acompanha a parte na correção do parcelamento e trava tirar a parte que tem estorno, como na compra à vista
- [ ] A tela "Todas as parcelas" deixa escolher a parte, também sem internet
- [ ] Testes de API e de navegador; verificações do projeto e PR para `main`
