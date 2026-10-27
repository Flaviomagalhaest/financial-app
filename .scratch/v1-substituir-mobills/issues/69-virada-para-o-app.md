# Virada: largar o Mobills

Type: task
Status: ready-for-human
Blocked by: 68, 35, 64
Skills: `run` (HITL: o dono faz no aparelho/na AWS e registra o resultado); apoio: `wizard`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #123
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 177

## O que construir

No dia da virada o casal passa a lançar só no app (HITL, do dono).

## Checklist

- [ ] Backup diário comprovadamente rodando e restauração testada no `dev` com o backup de `prod`
- [ ] Exportar o geral pela web e as faturas que faltam, incluindo a aberta; rodar a importação final e conferir a aba Conferência
- [ ] Informar o saldo de abertura de cada conta e o limite de cada cartão e confirmar quais faturas estão pagas
- [ ] Parar de lançar no Mobills; registrar a data em `## Answer`
- [ ] Verificações do projeto rodando e PR aberto para `main`
