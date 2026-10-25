# Ler a central de ajuda do Mobills e fazer uma exportação de teste

Type: task
Status: resolved
Blocked by: —
Skills: nenhuma de tipo; tarefa HITL (o dono abre a central de ajuda num navegador e faz a exportação de teste); apoio: `research` para consolidar o que o dono trouxer
Modelo recomendado: Sonnet
Effort recomendado: medium
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add3630d2d39b514227657b
Origem: pesquisa de [O que o Mobills exporta](01-o-que-o-mobills-exporta.md), que não leu a central de ajuda (Cloudflare) nem a tela de exportação (exige a conta do dono)

## Question

Que campos, formatos e limites a exportação do Mobills tem de verdade?

Só a central de ajuda e a tela de exportação respondem; o agente não alcança nenhuma das duas.

## Checklist

- [ ] (não feito; vira ticket 18) Dono abre `https://ajuda.mobills.com.br` num navegador, busca "exportar", "relatório", "backup" e "importar", e entrega à sessão os títulos e links dos artigos (ou o texto deles)
- [x] Dono faz uma exportação de teste pelo caminho que o artigo indicar (de preferência com poucos lançamentos) e entrega o arquivo à sessão fora do repositório; nada dele entra em commit
- [x] Agente grava em `## Answer` de [O que o Mobills exporta](01-o-que-o-mobills-exporta.md) o plano exigido, os formatos, os nomes das colunas de cada exportação, o limite de período e o que não sai, sem nenhum dado real
- [x] Se a exportação do app não bastar (bastou por ora; reavaliar no ticket 18), avaliar o pedido de portabilidade pela LGPD ao encarregado de dados do Mobills
- [x] Marcar [O que o Mobills exporta](01-o-que-o-mobills-exporta.md) como `resolved` e fechar este

## Answer

O dono não leu a central de ajuda (Cloudflare), mas entregou três exportações reais de teste (todas as transações de jul-ago, todas de setembro e só cartão de setembro). Elas respondem formato, colunas, tipos e limitações: ver `## Answer` de [O que o Mobills exporta](01-o-que-o-mobills-exporta.md), agora `resolved`. O que a central de ajuda ainda diria (plano exigido, limite de período) e as decisões de importação que a exportação levanta estão no [ticket 18](18-importacao-do-mobills-cartao-e-datas.md).
