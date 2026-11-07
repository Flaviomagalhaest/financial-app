# Desfazer da edição em lote nas partes: pular a compra ou a parte

Type: decision
Status: resolved
Blocked by: —
Skills: `grilling`, `domain-modeling` (HITL: decisão do dono); implementação nos tickets 201 e 202
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #479
Origem: [ticket 150](150-edicao-em-lote-na-compra-com-partes.md) (07/11). Na decisão, o dono aceitou que o desfazer pulasse **a parte** mudada depois do lote. A implementação pula **a compra inteira**: as partes são um campo só (ADR 0022, como no conflito sem internet) e o `PuladoNoDesfazer` é por lançamento. Além disso, qualquer mudança no campo `partes` depois do lote (inclusive só a descrição ou o valor de uma parte) pula a compra.

## O que decidir

- **Fica como está**: a compra volta inteira ou é pulada; mais simples e coerente com "as partes são um campo só".
- **Pular só a parte**: volta as outras partes da compra; o `PuladoNoDesfazer` ganha a parte, e a tela diz qual ficou.
- **Pular só quando a classificação da parte mudou**: a descrição ou o valor mudados depois não impedem o desfazer.

## Débito técnico achado na revisão do 150 (vale qualquer que seja a decisão)

Foi para o [ticket 202](202-contas-da-edicao-em-lote-com-partes.md).

- [ ] O desfazer conta cada lançamento como um no bloco de transação (`_desfazer_bloco`); a compra com muitas partes grava mais linhas. A aplicação já pesa as partes (`_blocos`), o desfazer não.
- [ ] O bloco da aplicação não pesa as partes do parcelamento que mudam junto com a primeira parcela do bloco.
- [ ] A parcela com partes refeitas "só esta" (ids que não vêm de `id_na_parcela`) não conta para as partes achadas do parcelamento na busca com filtro.
- [ ] No parcelamento com partes, `partes_que_mudam` conta as partes de cada parcela (3 parcelas × 2 partes = 6), não as 2 da compra; e a parcela cujas partes a busca não achou entra em `ja_estao_como_pedido`.

## Checklist

- [x] Decidir o comportamento
- [x] Gravar na ADR 0022 (a consequência do ticket 150)
- [x] Implementar com teste de API: vai para o [ticket 201](201-desfazer-do-lote-pula-so-a-parte.md) (e os débitos para o [202](202-contas-da-edicao-em-lote-com-partes.md))

## Answer

Decidido com o dono em 07/11: **pular só a parte, e só quando a classificação dela mudou**.

- O desfazer volta cada parte que o lote mudou e que ainda tem as categorias e as tags que o lote deu; pula só a parte cujas categorias, tags ou item mudaram depois (`mudou_depois`), a parte apagada (`excluido`) e a parte cuja categoria ou tag de antes saiu (`saiu`). As outras partes da compra voltam.
- Mudar a descrição, o valor, a pessoa ou a ordem das partes depois do lote não impede o desfazer.
- A parte criada depois do lote fica de fora; a compra que perdeu todas as partes é pulada inteira, como hoje.
- Vale igual nas partes do parcelamento e nas partes próprias de uma parcela.
- O `PuladoNoDesfazer` ganha `parte_id` e `parte_descricao`; a tela mostra uma linha por parte pulada ("Compra › Parte: motivo", ou "parte apagada por X", sem nome, sem migração para guardar a descrição). A compra conta em `desfeitos` se pelo menos uma parte voltou.
- O conflito sem internet continua com as partes como um campo só: é outro mecanismo.

Gravado na consequência da [ADR 0022](../../../docs/adr/0022-partes-da-compra.md). Os débitos da revisão do 150 ficam no [ticket 202](202-contas-da-edicao-em-lote-com-partes.md), depois do [201](201-desfazer-do-lote-pula-so-a-parte.md). Nenhum termo novo no glossário.
