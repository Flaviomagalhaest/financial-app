# Virada: largar o Mobills

Type: task
Status: ready-for-human
Blocked by: 68, 35, 64, 76, 91, 92
Skills: `run` (HITL: o dono faz no aparelho/na AWS e registra o resultado); apoio: `wizard`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #123
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 177

## O que construir

No dia da virada o casal passa a lançar só no app (HITL, do dono).

## Checklist

- [ ] Backup diário comprovadamente rodando e restauração testada no `dev` com o backup de `prod` ([ticket 76](76-restaurar-no-dev-o-backup-de-prod.md))
- [ ] Exportar o geral pela web e as faturas que faltam, incluindo a aberta; rodar a importação final e conferir a aba Conferência
- [ ] Gravar a importação final em `prod`: num banco vazio, `scripts/restaurar-backup.sh prod <importado.zip>`; com uma importação anterior, `--refazer-importacao` ([ticket 91](91-importador-do-mobills-gravar-e-refazer.md)), primeira vez dele no DSQL. Guardar em `## Answer` só as contagens da saída, que termina em "exportado de novo: mesmo zip"; se ela listar "informe de novo", refazer esses passos
- [ ] Informar o saldo de abertura de cada conta e o limite de cada cartão e confirmar quais faturas estão pagas
- [ ] Logo depois de restaurar, antes da tarefa diária rodar: dar o fechamento e o vencimento (`PATCH /api/cartoes/{id}/faturas/{mes}`) à fatura aberta e às fechadas ainda não pagas de cada cartão ativo. A importação traz toda fatura exportada sem datas, e o app a lê como paga ([ticket 68](68-importador-do-mobills-parcelamentos-pendentes-e-ajustes.md)); sem as datas, a parcela automática do mês seguinte vira realizada cedo
- [ ] Parar de lançar no Mobills; registrar a data em `## Answer`
- [ ] Verificações do projeto rodando e PR aberto para `main`
