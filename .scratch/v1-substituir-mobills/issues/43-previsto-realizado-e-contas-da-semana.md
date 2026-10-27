# Previsto, realizado, confirmação e contas da semana

Type: task
Status: ready-for-agent
Blocked by: 32
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #97
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 19, 105, 107, 108, 109, 110

## O que construir

Um compromisso futuro é um lançamento previsto que vira realizado ao ser confirmado ([ADR 0004](../../../docs/adr/0004-previsto-e-situacao-do-lancamento.md)); a tela inicial lembra o que confirmar.

## Checklist

- [ ] Situação previsto/realizado: só o realizado mexe no saldo; confirmar ajusta valor, data ou conta, inclusive sem internet (entra na fila)
- [ ] Previsto com data passada sem confirmação fica atrasado e continua contando na projeção e no "ainda dá para gastar"
- [ ] "N contas da semana para confirmar" na Hoje, com atrasados e previstos dos próximos 7 dias, em ordem de data, com "Confirmar" em um toque ou "Ajustar"
- [ ] Testes de API e de navegador
- [ ] Verificações do projeto rodando e PR aberto para `main`
