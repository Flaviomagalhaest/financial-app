# Estorno avulso: item do planejamento na tela, fatura negativa e testes no aparelho

Type: decision
Status: ready-for-human
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

- [ ] Decidir os três primeiros pontos e gravar no adendo da ADR 0016
- [ ] Abrir o ticket de implementação, com teste de API e de navegador
- [ ] Cobrir os testes que faltam
