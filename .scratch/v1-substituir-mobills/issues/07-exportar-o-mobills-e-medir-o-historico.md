# Exportar o Mobills e medir o histórico

Type: task
Status: resolved
Blocked by: —
Skills: nenhuma de tipo; tarefa HITL (o dono exporta, o agente mede)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #25
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Qual é o tamanho e a forma real do histórico do casal no Mobills?

O dono exporta os dados pelo caminho que [O que o Mobills exporta](01-o-que-o-mobills-exporta.md) descobrir. O agente mede sem copiar os dados para o repositório: quantidade de lançamentos por ano, de contas, cartões, faturas, tags e categorias; a lista de colunas de cada arquivo; e os casos estranhos (lançamento sem conta, valor zero, outra moeda, datas fora de ordem).

Os números servem a [Banco de dados e região](09-banco-de-dados-e-regiao.md) e à importação do Mobills.

## Checklist

- [x] Dono exporta os dados seguindo o passo a passo de O que o Mobills exporta
- [x] Os arquivos ficam fora do repositório (entregues à sessão ou numa pasta fora do clone); nada deles entra em commit
- [x] Agente mede e grava aqui, em `## Answer`, só contagens, nomes de colunas e casos estranhos, sem nenhum dado real

## Comments

- O dono já exportou 3 meses de teste (jul-set); falta o **histórico completo** para medir. Colunas e tipos estão no `## Answer` do [ticket 01](01-o-que-o-mobills-exporta.md). Para medir, são dois arquivos: todas as transações e só cartão (o geral não separa o cartão). Falta saber o limite de período por exportação ([ticket 18](18-importacao-do-mobills-cartao-e-datas.md)); se houver, exportar por trechos.
- Há um terceiro modo de exportação, por fatura de cartão e por mês (detalhes no `## Answer` do [ticket 01](01-o-que-o-mobills-exporta.md)). Para medir o histórico basta o export geral; as faturas mensais só entram para as datas de compra (decisão no [ticket 18](18-importacao-do-mobills-cartao-e-datas.md)), então não exporte fatura por fatura antes dessa decisão.

## Answer

Medido pelo dono com um script local (`medir-historico`, não versionado) sobre `data/historic/`, que fica fora do git (`data/` está no `.gitignore`). Só contagens, sem nenhum dado real. Período de 2019-02 a 2026-10, 7 anos e 8 meses.

**Transações** (o export geral, 4 arquivos de 2 anos; aba `Receitas e Despesas`, cabeçalho único de 8 colunas):

- **6.283 lançamentos** (5.967 despesas, 316 receitas). Por ano: 2019: 351, 2020: 468, 2021: 451, 2022: 380, 2023: 837, 2024: 1.068, 2025: 1.270, 2026: 1.458 (inclui lançamentos futuros até 2026-12-31).
- **Situação:** 5.972 `Paga` e **311 `Pendente`** (292 deles no arquivo 2025-2026): são os futuros, que viram previstos na [ADR 0004](../../../docs/adr/0004-previsto-e-situacao-do-lancamento.md).
- **Classificação:** 33 categorias distintas, **0 subcategorias**, **4 tags** distintas (todas no arquivo 2025-2026) e **1 conta só** (`Conta` não distingue banco, carteira ou cartão).
- **Transferências:** 0 linhas nos 4 arquivos.
- **Casos estranhos:** 0 sem data, 0 data inválida, 0 sem conta, 0 valor zero, 0 valor não numérico; 3 datas fora de ordem; 281 linhas idênticas (mesma data, descrição, valor e categoria) dentro do mesmo arquivo (7 + 6 + 124 + 144, ou seja, os arquivos não se sobrepõem); 889 lançamentos (14%) com o sufixo de parcela `(n/total)`.

**Cartões** (export por fatura, um arquivo por cartão e mês; 1 aba `Receitas`, cabeçalho único de 4 colunas: `Data`, `Descrição`, `Categoria`, `Valor`):

- **7 pastas de cartão** (o dono esperava 6: ver [ticket 18](18-importacao-do-mobills-cartao-e-datas.md)) e **219 faturas**, **4.742 lançamentos** (90 negativos, estornos ou créditos), 25 categorias distintas. Por ano da compra: 2019: 234, 2020: 297, 2021: 280, 2022: 252, 2023: 750, 2024: 855, 2025: 1.140, 2026: 934.
- **Por cartão** (faturas; primeira a última; lançamentos): cartão 1: 88; 201904-202607; 898. Cartão 2: 30; 202110-202403; 288. Cartão 3: 40; 202305-202608; 3.188. Cartão 4: 26; 201903-202109; 158. Cartão 5: 29; 202103-202307; 50. Cartão 6: 1; 202609; 127. Cartão 7: 5; 202605-202609; 33.
- **Faturas ausentes ou vazias** significam mês sem compras, segundo o dono: o cartão 4 não tem 5 meses (201905, 201906, 201907, 201910, 201911), e 6 faturas vieram vazias (cartões 1, 2 e 5, nos últimos dois meses de cada um).
- **Casos estranhos:** 0 sem data, 0 valor zero, 0 valor não numérico; 204 linhas fora de ordem de data dentro das faturas (ordem não confiável); 685 linhas idênticas (mesma data, descrição, valor e categoria), 588 só no cartão 3. Hipótese não confirmada: uma compra parcelada reaparece em cada fatura com a mesma data de compra, o que as torna "repetidas" entre faturas, e o número da parcela não vem (só 1 linha com `(n/total)` em 4.742).
- **Sobreposição com as transações:** as compras de cartão estão também no export geral (na data do vencimento da fatura), então somar as duas fontes duplica; 4.742 contra 5.967 despesas indica cerca de 80%, sem cruzamento linha a linha (ticket 18).

**Volume:** cerca de 11 mil linhas em 7 anos e 8 meses (6.283 + 4.742), cerca de 2.400 por ano nos últimos dois anos. Estimativa de quem mede: poucos MB, bem abaixo dos 13 a 61 MB da pesquisa do [ticket 03](03-banco-de-dados-na-aws.md); o banco não precisa se preocupar com o tamanho do histórico. Serve ao [ticket 09](09-banco-de-dados-e-regiao.md).
