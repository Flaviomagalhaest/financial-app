# Contas da edição em lote com partes

Type: task
Status: claimed
Blocked by: 201
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #515
Origem: [ticket 191](191-desfazer-do-lote-nas-partes.md): débito técnico achado na revisão do [ticket 150](150-edicao-em-lote-na-compra-com-partes.md). Bloqueado pelo 201 porque mexe nas mesmas funções do desfazer.

## O que construir

Quatro contas da edição em lote erram na compra com partes, sem mudar o comportamento que o casal vê, a não ser a prévia e os blocos de transação:

- **Bloco do desfazer**: o desfazer conta cada lançamento como um no bloco de uma transação; a compra com muitas partes grava mais linhas. Ele passa a pesar as partes, como a aplicação já pesa.
- **Bloco da aplicação**: as partes do parcelamento que mudam junto com a primeira parcela do bloco também pesam.
- **Busca com filtro**: as partes refeitas "só esta" numa parcela (que não vêm do parcelamento) contam para as partes achadas do parcelamento.
- **Prévia do parcelamento com partes**: as partes que mudam contam as partes da compra (2), não as de cada parcela (3 parcelas × 2 partes = 6); a parcela cujas partes a busca não achou não entra em "já estão como pedido".

## Checklist

- [ ] Teste de API: a compra com muitas partes se desfaz em blocos que cabem numa transação
- [ ] Teste de API: o bloco da aplicação conta as partes do parcelamento que mudam com a primeira parcela
- [ ] Teste de API: na busca com filtro, as partes "só esta" de uma parcela contam como achadas
- [ ] Teste de API: a prévia do parcelamento com partes conta as partes da compra, e a parcela sem partes achadas fica fora de "já estão como pedido"
- [ ] Implementar no servidor
