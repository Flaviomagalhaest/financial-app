# Recorrência: mudar, pular, encerrar e excluir

Type: task
Status: ready-for-agent
Blocked by: 44
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #99
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 90, 91, 92, 93, 94, 111

## O que construir

O casal acompanha um reajuste ou uma cobrança atípica sem mexer no passado.

## Checklist

- [ ] Mudar "daqui para frente" em qualquer campo; mudar só um mês, preservado de mudanças posteriores; pular um mês
- [ ] Encerrar ou excluir apaga os previstos depois da data de fim; mudar nunca reescreve um realizado
- [ ] A recorrência guarda a escolha do item do planejamento (quando o ticket de item existir, o campo já nasce aqui)
- [ ] Mudança de regra que colide com edição offline vira conflito marcado como vindo da regra ([ticket 34](34-conflito-de-campos.md)): a regra grava pelo `registrar_mudancas(..., origem=origem(regra.descricao))` (`backend/app/recorrencias.py`, como a tarefa diária do ticket 44 faz ao realizar o automático) e sobe a versão do lançamento com `subir_versao`, e a tela de conflito já mostra "O da regra <origem>"
- [ ] Os previstos de uma regra são os lançamentos com o `recorrencia_id` dela; o id de cada um é `uuid5(regra, número da ocorrência)` e `recorrencias.geradas` diz até que ocorrência já gerou (ticket 44). Mudar "daqui para frente" regera só os previstos não alterados à mão (falta a marca de alterado à mão no lançamento); pular é excluir o previsto, que a geração não traz de volta
- [ ] Conta ou categoria arquivada depois: hoje a tarefa diária segue gerando previstos nelas (a regra já as tinha). Decidir se arquivar a conta encerra ou avisa nas recorrências dela
- [ ] Testes de API
- [ ] Verificações do projeto rodando e PR aberto para `main`
