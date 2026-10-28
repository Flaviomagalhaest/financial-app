# Orçamento e alarmes de custo e de erros

Type: task
Status: ready-for-human
Blocked by: 28
Skills: `implement`, `tdd`; apoio: `run`; HITL no que falta (o dono publica a pilha e confirma o e-mail)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #83
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 178, 179

## O que construir

O dono é avisado por e-mail quando o custo ou os erros fogem do esperado, sem que os créditos escondam o gasto.

## Checklist

- [x] Orçamento sem créditos com alertas em US$ 1 (real), US$ 5 (previsão) e US$ 5 (real), no mesmo código do CDK
- [x] Alarme de erros 5xx da API acima de um limite por dia, por e-mail
- [ ] Confirmado pela entrega de um alerta de teste no e-mail do dono
- [ ] Dono confirma os valores provisórios: limite de 5 respostas 5xx por dia (`infra/lib/pilha-app.ts`) e teto de US$ 5 do orçamento (`infra/lib/pilha-orcamento.ts`)
- [x] Verificações do projeto rodando e PR aberto para `main`

Pendente do dono (HITL), por isso o ticket fica `ready-for-human` até fechar: publicar `financial-orcamento` com credenciais da conta, confirmar a inscrição do SNS nas pilhas do app e disparar um alerta de teste (`aws sns publish` no tópico `Avisos`).
