# Recorrência: mudar, pular e encerrar pela tela e sem internet

Type: task
Status: ready-for-agent
Blocked by: 86
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Opus
Effort recomendado: high
Issue: #177
Origem: [ticket 45](45-recorrencia-mudar.md) (só a API existe: `PATCH` e `DELETE /api/recorrencias/{id}`); spec da v1, histórias de usuário 90, 91, 92, 93

## O que construir

O casal muda, pula e encerra uma recorrência na tela, e o pedido sobe com a fila quando não há internet.

## Checklist

- [ ] No previsto de uma recorrência: "Só este mês" (edição comum do lançamento, que o marca como alterado à mão), "Daqui para frente" (`PATCH /api/recorrencias/{id}` com `a_partir_da_ocorrencia` = a `ocorrencia` do previsto), "Pular este mês" (excluir o previsto) e "Encerrar" (`ate` ou `vezes`)
- [ ] Excluir a recorrência inteira (`DELETE /api/recorrencias/{id}`): avisar que o atrasado e o realizado ficam
- [ ] Ações `alterar_recorrencia` e `excluir_recorrencia` em `POST /api/lancamentos/lote` (`backend/app/lancamentos.py`, `Acao`), e a fila do app (`web/src/dados/fila.ts`) guarda cada pedido como um item só
- [ ] Mostrar na tela de conflito "O da regra <origem>" (a `origem` já vem no 409)
- [ ] Alterar a recorrência não tem versão: duas pessoas mudando a regra ao mesmo tempo ficam com a última a chegar; decidir se isso basta (ADR 0011)
- [ ] Testes de API das ações no lote e de navegador do fluxo, online e sem internet
- [ ] Verificações do projeto rodando e PR aberto para `main`
