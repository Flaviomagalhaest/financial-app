# Itens do planejamento do mês

Type: task
Status: resolved
Blocked by: 40
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #103
Origem: [spec da v1](../spec.md), etapa 4; histórias de usuário 112, 117, 118, 119

## O que construir

O casal planeja o mês por item ("R$ 1.000 em alimentação") e vê o realizado, o previsto, o planejado e a porcentagem de cada um.

## Checklist

- [x] Itens por mês, cada um de uma categoria (inclusive de transferência, para planejar o que guardar) e com um valor; edição só com internet
- [x] Por item: realizado, previsto, planejado e %; "ainda dá para gastar" do item é planejado menos realizado e previsto, e o do mês é a soma do que falta em cada item, sem compensar item estourado
- [x] Leitura do planejamento de um mês numa chamada só, já somada no servidor
- [x] Testes de API com exemplos concretos
- [x] Juntar categorias (`POST /api/categorias/{id}/juntar`) também move os itens do planejamento e as escolhas de item, e excluir categoria recusa se há item (hoje a API só olha lançamentos; ticket 40)
- [x] Verificações do projeto rodando e PR aberto para `main`
- [x] O "ainda dá para gastar" conta o previsto atrasado (data passada, sem confirmação; campo `atrasado` do ticket 43) até ele ser confirmado ou excluído (história 108): somar todo previsto do mês, não só o de data futura

## Notas da implementação

- Tabela `itens_do_planejamento` (migration 0018, `mes` é o primeiro dia do mês) e `backend/app/planejamento.py`; formato do backup na versão 8, com conversor da 7.
- Porcentagem = (realizado + previsto) / planejado, arredondada; o "ainda dá para gastar" do mês soma só o que sobra, e item estourado entra com zero.
- Lançamento com mais de uma categoria com item no mês ainda não conta em item nenhum (a escolha é do [51](51-item-do-lancamento-e-a-escolher.md)); transferência com categoria conta no item dessa categoria.
- Juntar categorias que têm item no mesmo mês soma os valores num item do destino; também move a categoria das transferências, e excluir categoria recusa se há transferência com ela.
- **Pendências**: linhas novas nos tickets [51](51-item-do-lancamento-e-a-escolher.md) (juntar categorias também precisa mover as escolhas de item; a leitura do mês precisa usar a escolha) e [37](37-cartoes-e-faturas.md) (o planejamento lê o mês pela data; passar a ler o mês em que o lançamento conta).
- **Revisão**: a unicidade de (mês, categoria) é conferida na rota, sem índice único: dois POSTs simultâneos de ids diferentes para a mesma categoria poderiam criar dois itens. Com dois usuários o risco é mínimo; o índice único (`CREATE UNIQUE INDEX ASYNC` no DSQL) fica para quando o [35](35-teste-nos-dois-celulares.md) conferir no DSQL; linha nova nele.
