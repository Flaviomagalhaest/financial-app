# Importador do Mobills: linha de fatura duplicada pelo Mobills

Type: task
Status: ready-for-human
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

- [ ] Decisão do dono: descartar sozinho ou decidir na planilha
- [ ] O importador reconhece a linha de fatura sem par que repete data, valor e cartão de uma casada
- [ ] Teste: a fatura do cenário fecha sem a linha duplicada; duas compras iguais de verdade não somem sem decisão
- [ ] Rodar de novo nos exports reais: a fatura do Personnalite de 2023-11 dá 7.824,93 e a Conferência de 2023-11 dá diferença 0
