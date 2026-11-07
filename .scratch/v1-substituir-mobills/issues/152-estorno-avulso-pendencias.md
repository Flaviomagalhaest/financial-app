# Estorno avulso: item do planejamento na tela, fatura negativa e testes no aparelho

Type: decision
Status: resolved
Blocked by: —
Skills: `grilling`, `domain-modeling` (HITL: decisão do dono); depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #349
Origem: [ticket 135](135-estorno-avulso.md): pendências da revisão (Spec) do estorno avulso

## O que decidir e fazer

- **Item do planejamento na tela do crédito.** A tela "Lançar crédito" esconde o aviso de planejamento e não pergunta o item. Com duas categorias que têm item no mês, o crédito novo cai em "A escolher" na Hoje, sem escolha na hora (o estorno ligado a compra herda o item dela). Decidir: perguntar o item na tela do avulso (como na compra) ou deixar "A escolher".
- **Fatura com total negativo.** O avulso não tem limite de valor (Q15), então a fatura pode ficar com total negativo (a soma dos créditos passa das compras). Decidir o que é "a pagar" nesse caso e o que a tela mostra; hoje só o total sai negativo.
- **Mês sem fatura.** "Lançar crédito" só aparece com a fatura do mês já criada. Decidir se o cartão sem fatura no mês também lança (a data decide a fatura).
- **Testes que faltam**: o avulso na busca e no histórico (soma do aparelho em `dados/busca.ts`), no limite do cartão e na projeção; a tag e a pessoa pela tela (o e2e só cobre categoria).
- **Defeitos que o estorno ligado a compra também tem**: a linha "A escolher" da Hoje mostra o valor sem sinal de crédito (`TelaHoje.tsx`).

## Checklist

- [x] Decidir os três primeiros pontos e gravar no adendo da ADR 0016
- [x] Abrir o ticket de implementação, com teste de API e de navegador ([ticket 189](189-estorno-avulso-item-fatura-e-testes.md))
- [x] Cobrir os testes que faltam: passaram para o [ticket 189](189-estorno-avulso-item-fatura-e-testes.md), com o sinal de crédito da "A escolher"

## Answer

Decidido com o dono (grilling):

- **Item do planejamento**: a tela "Lançar crédito" pergunta o item como na compra; "A escolher" fica para o que chegar sem escolha.
- **Fatura com total negativo**: o servidor recusa o avulso que deixaria o devido da fatura abaixo de zero, só ao salvar o avulso (criação e edição). Os outros caminhos não ganham trava e o aparelho não confere: o cenário é raro, e a ADR 0021 segue sem saldo anterior negativo.
- **Mês sem fatura**: "Lançar crédito" aparece em qualquer mês não pago; a data decide a fatura, que nasce com as datas padrão.
- Tudo vai num ticket de implementação só, o [189](189-estorno-avulso-item-fatura-e-testes.md). Adendo do ticket 152 na [ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md); verbete "Estorno avulso" do `GLOSSARY.md` atualizado.
