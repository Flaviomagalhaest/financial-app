# Exportar o Mobills e medir o histórico

Type: task
Status: ready-for-human
Blocked by: —
Skills: nenhuma de tipo; tarefa HITL (o dono exporta, o agente mede)
Modelo recomendado: Sonnet
Effort recomendado: medium
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add2e70c4d860fcf9d6eb6d
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Qual é o tamanho e a forma real do histórico do casal no Mobills?

O dono exporta os dados pelo caminho que [O que o Mobills exporta](01-o-que-o-mobills-exporta.md) descobrir. O agente mede sem copiar os dados para o repositório: quantidade de lançamentos por ano, de contas, cartões, faturas, tags e categorias; a lista de colunas de cada arquivo; e os casos estranhos (lançamento sem conta, valor zero, outra moeda, datas fora de ordem).

Os números servem a [Banco de dados e região](09-banco-de-dados-e-regiao.md) e à importação do Mobills.

## Checklist

- [ ] Dono exporta os dados seguindo o passo a passo de O que o Mobills exporta
- [ ] Os arquivos ficam fora do repositório (entregues à sessão ou numa pasta fora do clone); nada deles entra em commit
- [ ] Agente mede e grava aqui, em `## Answer`, só contagens, nomes de colunas e casos estranhos, sem nenhum dado real

## Comments

- O dono já exportou 3 meses de teste (jul-set); falta o **histórico completo** para medir. Colunas e tipos estão no `## Answer` do [ticket 01](01-o-que-o-mobills-exporta.md). Para medir, são dois arquivos: todas as transações e só cartão (o geral não separa o cartão). Falta saber o limite de período por exportação ([ticket 18](18-importacao-do-mobills-cartao-e-datas.md)); se houver, exportar por trechos.
- Há um terceiro modo de exportação, por fatura de cartão e por mês (detalhes no `## Answer` do [ticket 01](01-o-que-o-mobills-exporta.md)). Para medir o histórico basta o export geral; as faturas mensais só entram para as datas de compra (decisão no [ticket 18](18-importacao-do-mobills-cartao-e-datas.md)), então não exporte fatura por fatura antes dessa decisão.
