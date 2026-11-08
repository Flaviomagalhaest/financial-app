# Contas do lote com a parcela "só esta" de outra forma que o parcelamento

Type: task
Status: resolved
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

- [x] Teste de API: parcela "só esta" com as partes em outra ordem
- [x] Teste de API: parcela "só esta" com outra quantidade de partes
- [x] Teste de API: parcelamento misto (parcela com e sem partes) nos blocos da aplicação
- [x] Decidir se o desfazer passa a pesar como a aplicação: **não**. O desfazer pesa o que o lote gravou de fato (`edicao_em_lote_partes`), que é o custo real; a aplicação pesa as partes do parcelamento inteiro, por segurança. O desfazer nunca pesa mais que a aplicação, então o bloco dele cabe.
- [x] Implementar no servidor

## Feito

`_posicoes_na_regra` casa a parte "só esta" com a do parcelamento pelo id derivado, ou pela descrição e pessoa quando só uma de cada lado tem o par (sem distinguir e com a mesma quantidade, pela posição). `_partes_que_mudam` conta pelas posições assim casadas e `_blocos` pesa o parcelamento pelas partes dele (`_Plano.partes_do_parcelamento`).

Limite conhecido: com quantidade de partes diferente, a parte "só esta" sem par único por descrição e pessoa fica de fora da busca (sem aviso). Não há teste do parcelamento misto (parcelas com e sem partes juntas): o teste cobre o parcelamento com partes e todas as parcelas sem elas.
