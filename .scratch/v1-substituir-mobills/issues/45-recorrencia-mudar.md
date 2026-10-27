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
- [ ] Mudança de regra que colide com edição offline vira conflito marcado como vindo da regra ([ticket 34](34-conflito-de-campos.md))
- [ ] Testes de API
- [ ] Verificações do projeto rodando e PR aberto para `main`
