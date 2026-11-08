# Contas do lote com a parcela "só esta" de outra forma que o parcelamento

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #540
Origem: revisão do [ticket 202](202-contas-da-edicao-em-lote-com-partes.md): o 202 casa as partes "só esta" com as do parcelamento pela **posição**, e pesa o parcelamento com as partes da primeira parcela. Vale quando a parcela tem as mesmas partes na mesma ordem; fora disso erra.

## O que construir

- **Ordem trocada**: a parcela "só esta" com as partes em outra ordem casa a parte errada (`_partes_do_parcelamento_achadas`, `_partes_que_mudam`).
- **Quantidade diferente**: a parcela com outra quantidade de partes sai de "achadas" e de "já estão como pedido", e infla ou deflaciona `partes_que_mudam`.
- **Peso do bloco da aplicação**: `_blocos` pesa o parcelamento com as partes da primeira parcela vista; devia pesar as da regra (`ler_um(...).partes`) ou as que mudam. Parcelamento misto (parcela com e sem partes) pesa errado.
- **Peso do desfazer**: pesa só as partes que o lote mudou, enquanto `_blocos` pesa todas (conservador, mas diverge).

## Checklist

- [ ] Teste de API: parcela "só esta" com as partes em outra ordem
- [ ] Teste de API: parcela "só esta" com outra quantidade de partes
- [ ] Teste de API: parcelamento misto (parcela com e sem partes) nos blocos da aplicação
- [ ] Decidir se o desfazer passa a pesar como a aplicação
- [ ] Implementar no servidor
