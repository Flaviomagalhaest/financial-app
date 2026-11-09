# Importador do Mobills: linha de fatura duplicada pelo Mobills

Type: task
Status: resolved
Blocked by: —
Skills: `grilling` (HITL: o dono decide entre descartar sozinho ou pedir a decisão na planilha); depois `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #567
Origem: [ticket 92](92-rodar-o-importador-nos-exports-reais.md) (a fatura do Personnalite de 2023-11 deu 8.021,23 contra 7.824,93 no PDF do banco; a diferença de 196,30 são duas linhas que o Mobills duplicou no export)

## O que construir

O dono conferiu no PDF do banco: as compras "Coisas de cozinha" (149,62) e o 46,68 de 19/11/2023 aparecem **uma vez só**, e o export do Mobills (e o app) as mostra duas. É bug do Mobills: o arquivo `202311.xlsx` do Personnalite traz uma linha a mais de cada, sem par no geral. Hoje o importador as inclui como compras do cartão (regra do ticket 18 para a linha de fatura sem par), e a fatura e o mês ficam 196,30 acima do banco.

Nos exports reais são **3 linhas** de fatura sem par que repetem a data e o valor de uma linha já casada (todas de 2023, soma 215,05), de 114 linhas sem par; as outras 111 não repetem nada e a regra do ticket 18 continua valendo para elas (86 são créditos, soma -11.563,23).

A decidir (`grilling`): a linha sem par que repete data, valor e cartão de uma linha casada (a descrição e a categoria podem variar: "Mercado" contra "Alimentação") é descartada sozinha, ou vai para uma aba da planilha com coluna de decisão (como a `Pares prováveis`)? Com só 3 casos, a aba é o caminho seguro; o descarte automático pode engolir uma compra repetida de verdade (duas compras iguais no mesmo dia).

## Checklist

- [x] Decisão do dono: descartar sozinho ou decidir na planilha
- [x] O importador reconhece a linha de fatura sem par que repete data, valor e cartão de uma casada
- [x] Teste: a fatura do cenário fecha sem a linha duplicada; duas compras iguais de verdade não somem sem decisão
- [x] Rodar de novo nos exports reais: a fatura do Personnalite de 2023-11 dá 7.824,93 e a Conferência de 2023-11 dá diferença 0 (a fatura dá 7.824,93; a diferença da Conferência depende da coluna Mobills, que é do dono preencher)

## Comments

- Do [ticket 216](216-importador-do-mobills-decisao-para-grupos-ambiguos-e-parcelas-quebradas.md): nos grupos ambíguos, a pendente duplicada (e a linha de fatura que repete a data e o cartão de uma casada) agora fica de fora da importação, mas não aparece na Conferência nem na aba Faturas. Se o total do Mobills a inclui, a diferença do mês fica sem explicação. Ao resolver este ticket, mostrar o que foi descartado lá também.

## Answer

Decisão do dono (grilling, 2026-11-08): **aba com decisão**, não descarte automático.

### O que foi feito

- Aba nova `Faturas repetidas`: cada linha de fatura sem par que repete cartão, data e valor de uma linha casada, com a descrição e a categoria da linha casada ao lado. Coluna `Decisão (descartar ou manter)`: **em branco ou `manter` deixa a linha entrar como compra** (como hoje); só `descartar` a tira. A decisão fica entre as rodadas pela chave (cartão, mês, data, descrição, valor) e uma decisão fora das válidas vira impedimento.
- Pendência do [ticket 216](216-importador-do-mobills-decisao-para-grupos-ambiguos-e-parcelas-quebradas.md) resolvida: o que o Mobills duplicou e o importador deixou de fora (as repetidas descartadas aqui e as descartadas dos grupos ambíguos) aparece no "Por quê" da Conferência e, agora, numa coluna `Por quê` da aba Faturas.
- Teste: a linha repetida entra até o dono decidir, `manter` não a tira, `descartar` tira, a fatura e a Conferência explicam, e uma compra de outra data não cai na aba.

### Nos exports reais

A aba lista 4 linhas (o ticket contava 3; a quarta é o Amaciante de 32,99 em 2023-10, que sobrou depois do ticket 216). Com `descartar` nas duas de 2023-11 (Coisas de cozinha 149,62 e 46,68), a fatura do Personnalite de 2023-11 dá **7.824,93**, como o PDF do banco. A decisão sobre as de 2023-10 e a coluna Mobills da Conferência são do dono.

### Limite conhecido

Duas linhas idênticas (mesma chave) na aba dividem a decisão, como nos grupos ambíguos.
