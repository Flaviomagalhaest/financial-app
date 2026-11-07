# Desfazer da edição em lote nas partes: pular a compra ou a parte

Type: decision
Status: ready-for-human
Blocked by: —
Skills: `grilling`, `domain-modeling` (HITL: decisão do dono); depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #479
Origem: [ticket 150](150-edicao-em-lote-na-compra-com-partes.md) (07/11). Na decisão, o dono aceitou que o desfazer pulasse **a parte** mudada depois do lote. A implementação pula **a compra inteira**: as partes são um campo só (ADR 0022, como no conflito sem internet) e o `PuladoNoDesfazer` é por lançamento. Além disso, qualquer mudança no campo `partes` depois do lote (inclusive só a descrição ou o valor de uma parte) pula a compra.

## O que decidir

- **Fica como está**: a compra volta inteira ou é pulada; mais simples e coerente com "as partes são um campo só".
- **Pular só a parte**: volta as outras partes da compra; o `PuladoNoDesfazer` ganha a parte, e a tela diz qual ficou.
- **Pular só quando a classificação da parte mudou**: a descrição ou o valor mudados depois não impedem o desfazer.

## Débito técnico achado na revisão do 150 (vale qualquer que seja a decisão)

- [ ] O desfazer conta cada lançamento como um no bloco de transação (`_desfazer_bloco`); a compra com muitas partes grava mais linhas. A aplicação já pesa as partes (`_blocos`), o desfazer não.
- [ ] O bloco da aplicação não pesa as partes do parcelamento que mudam junto com a primeira parcela do bloco.
- [ ] A parcela com partes refeitas "só esta" (ids que não vêm de `id_na_parcela`) não conta para as partes achadas do parcelamento na busca com filtro.
- [ ] No parcelamento com partes, `partes_que_mudam` conta as partes de cada parcela (3 parcelas × 2 partes = 6), não as 2 da compra; e a parcela cujas partes a busca não achou entra em `ja_estao_como_pedido`.

## Checklist

- [ ] Decidir o comportamento
- [ ] Gravar na ADR 0022 (a consequência do ticket 150)
- [ ] Implementar com teste de API
