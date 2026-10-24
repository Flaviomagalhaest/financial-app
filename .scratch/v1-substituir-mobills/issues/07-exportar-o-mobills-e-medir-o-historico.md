# Exportar o Mobills e medir o histórico

Type: task
Status: open
Blocked by: 01
Skills: nenhuma de tipo; tarefa HITL (o dono exporta, o agente mede)
Modelo recomendado: Sonnet
Effort recomendado: medium
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Qual é o tamanho e a forma real do histórico do casal no Mobills?

O dono exporta os dados pelo caminho que [O que o Mobills exporta](01-o-que-o-mobills-exporta.md) descobrir. O agente mede sem copiar os dados para o repositório: quantidade de lançamentos por ano, de contas, cartões, faturas, tags e categorias; a lista de colunas de cada arquivo; e os casos estranhos (lançamento sem conta, valor zero, outra moeda, datas fora de ordem).

Os números servem a [Banco de dados e região](09-banco-de-dados-e-regiao.md) e à importação do Mobills.

## Checklist

- [ ] Dono exporta os dados seguindo o passo a passo de O que o Mobills exporta
- [ ] Os arquivos ficam fora do repositório (entregues à sessão ou numa pasta fora do clone); nada deles entra em commit
- [ ] Agente mede e grava aqui, em `## Answer`, só contagens, nomes de colunas e casos estranhos, sem nenhum dado real
