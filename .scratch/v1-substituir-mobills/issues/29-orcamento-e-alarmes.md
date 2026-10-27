# Orçamento e alarmes de custo e de erros

Type: task
Status: ready-for-agent
Blocked by: 28
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #83
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 178, 179

## O que construir

O dono é avisado por e-mail quando o custo ou os erros fogem do esperado, sem que os créditos escondam o gasto.

## Checklist

- [ ] Orçamento sem créditos com alertas em US$ 1 (real), US$ 5 (previsão) e US$ 5 (real), no mesmo código do CDK
- [ ] Alarme de erros 5xx da API acima de um limite por dia, por e-mail
- [ ] Confirmado pela entrega de um alerta de teste no e-mail do dono
- [ ] Verificações do projeto rodando e PR aberto para `main`
