# Recorrência: mudar, pular, encerrar e excluir

Type: task
Status: resolved
Blocked by: 44
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #99
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 90, 91, 92, 93, 94, 111

## O que construir

O casal acompanha um reajuste ou uma cobrança atípica sem mexer no passado.

## Checklist

- [x] Mudar "daqui para frente" em qualquer campo; mudar só um mês, preservado de mudanças posteriores; pular um mês
- [x] Encerrar ou excluir apaga os previstos depois da data de fim; mudar nunca reescreve um realizado
- [x] A recorrência guarda a escolha do item do planejamento (quando o ticket de item existir, o campo já nasce aqui)
- [x] Mudança de regra que colide com edição offline vira conflito marcado como vindo da regra ([ticket 34](34-conflito-de-campos.md)): a regra grava pelo `registrar_mudancas(..., origem=origem(regra.descricao))` (`backend/app/recorrencias.py`, como a tarefa diária do ticket 44 faz ao realizar o automático) e sobe a versão do lançamento com `subir_versao`, e a tela de conflito já mostra "O da regra <origem>"
- [x] Os previstos de uma regra são os lançamentos com o `recorrencia_id` dela; o id de cada um é `uuid5(regra, número da ocorrência)` e `recorrencias.geradas` diz até que ocorrência já gerou (ticket 44). Mudar "daqui para frente" regera só os previstos não alterados à mão (a marca de alterado à mão é a de campo com `origem` vazia, veja as notas); pular é excluir o previsto, que a geração não traz de volta
- [x] Conta ou categoria arquivada depois: hoje a tarefa diária segue gerando previstos nelas (a regra já as tinha). Decidir se arquivar a conta encerra ou avisa nas recorrências dela (decisão do dono: [ticket 94](94-conta-ou-categoria-arquivada-com-recorrencia-ativa.md))
- [x] Testes de API
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- API em `backend/app/recorrencias.py`:
  - `PATCH /api/recorrencias/{id}` muda a regra "daqui para frente". `a_partir_da_ocorrencia` diz de qual ocorrência vale; os outros campos são os da regra (`tipo`, `valor_centavos`, `tipo_do_valor`, `automatico`, `descricao`, `conta_id`, `categoria_ids`, `tags`, `pessoa`, `item_id`, `a_cada`, `unidade`, `inicio`, `ate`, `vezes`), e o que não vem fica como está. Mandar `ate` tira `vezes` e vice-versa; `null` tira o fim. A ocorrência precisa existir ou ser a próxima a gerar (422).
  - `DELETE /api/recorrencias/{id}` é idempotente (204). Tira a regra e os previstos de hoje em diante; o realizado e o atrasado ficam (história 108: nada some sem o casal confirmar ou excluir) como lançamentos que a regra gerou.
- Os previstos que mudam são os da ocorrência dada em diante, ainda previstos e não excluídos, e que ninguém alterou à mão. "Alterado à mão" é ter algum campo com `origem` vazia em `lancamento_campos` (edição de uma pessoa); a regra grava com `origem`, então a mudança seguinte da regra ainda os alcança. Por isso não houve coluna nova no lançamento. A regra grava com `registrar_mudancas(..., origem=origem(descricao))` e sobe a versão com `subir_versao`, e a edição sem internet sobre a versão de antes recebe o 409 "O da regra ...". O realizado nunca é tocado.
- Encerrar (`ate` ou `vezes`) exclui, com a marca de exclusão, todo previsto depois do fim, também o alterado à mão. Pular um mês é excluir o previsto (`DELETE /api/lancamentos/{id}`), que a geração e as mudanças não trazem de volta; mudar só um mês é a edição comum do lançamento.
- Calendário: `inicio` passa a ser a data da ocorrência em que a mudança começou e `ocorrencia_do_inicio` (migration 0037) diz qual é, para a numeração e os ids dos previstos continuarem os mesmos. Escolha do item do planejamento: `item_id` na regra (migration 0036), sem chave estrangeira.
- O reajuste vai em lotes de uma transação (a folga do DSQL), como a geração; se parar no meio, repetir o `PATCH` continua. `excluir` e `gravar_categorias` de `lancamentos.py` deixaram de ser privados para a regra usá-los.
- Backup na versão 13, com o conversor da 12 (item e ocorrência do início).
- Pendências gravadas: tela e fila no [93](93-recorrencia-mudar-pela-tela-e-sem-internet.md), conta ou categoria arquivada no [94](94-conta-ou-categoria-arquivada-com-recorrencia-ativa.md), reabrir o fim e reagendar sem buraco no [95](95-recorrencia-reabrir-e-reagendar-sem-buraco.md) e os previstos herdarem o `item_id` no [51](51-item-do-lancamento-e-a-escolher.md).
