# Aba Futuro e projeção de saldo

Type: task
Status: ready-for-agent
Blocked by: 48, 51
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #112
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 135, 136

## O que construir

O casal sabe se vai fechar no azul nos próximos meses.

## Checklist

- [ ] Projeção com o realizado no passado e duas linhas adiante (só previstos, e descontando o que falta do planejamento), mais tabela dos próximos meses
- [ ] A fatura é descontada no mês dela
- [ ] Testes de API com exemplos concretos
- [ ] Verificações do projeto rodando e PR aberto para `main`
- [ ] A linha "só previstos" conta também o previsto atrasado (data passada, sem confirmação; campo `atrasado` do ticket 43) até ele ser confirmado ou excluído (história 108), e não só os de data futura
