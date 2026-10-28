# Recorrência: criar

Type: task
Status: ready-for-agent
Blocked by: 43
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #98
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 87, 88, 89, 105, 106

## O que construir

O casal cadastra o salário, a luz ou o seguro anual uma vez só e os previstos aparecem sozinhos.

## Checklist

- [ ] Recorrência a cada N semanas ou N meses, sem fim, até uma data ou por N vezes; dia 31 em mês curto cai no último dia
- [ ] Valor fixo ou estimado; só a de valor fixo pode ser automática (vira realizada sozinha na data); a estimada sempre pede confirmação
- [ ] Previstos gerados até o horizonte de 24 meses, estendido por uma tarefa diária (EventBridge) que também realiza os automáticos
- [ ] Testes de API com datas de fim de mês e com a tarefa diária
- [ ] Verificações do projeto rodando e PR aberto para `main`
- [ ] Previsto automático não pede confirmação (ticket 43): fica fora de `GET /api/contas-da-semana` e não aparece como `atrasado`, que hoje valem para todo `situacao = 'previsto'`
