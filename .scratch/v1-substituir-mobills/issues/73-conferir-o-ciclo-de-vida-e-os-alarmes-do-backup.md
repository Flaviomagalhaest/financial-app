# Conferir na AWS o ciclo de vida e os alarmes do backup

Type: task
Status: ready-for-human
Blocked by: 64
Skills: `wizard` para guiar os passos do dono; HITL (credencial AWS do dono e dias de espera)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #137
Origem: [ticket 64](64-backup-diario.md) (a regra de ciclo de vida e os alarmes só foram sintetizados e publicados; a expiração depende de dias passarem) e o item do [ticket 20](20-configurar-o-acesso-a-conta-aws.md) sobre a documentação ambígua

## O que fazer

A documentação da AWS diz que o ciclo de vida não apaga uma versão travada pelo Object Lock, mas não diz com clareza se ele a apaga depois que a trava vence. Sem isso, o bucket do backup cresce sem fim (em centavos). O `dev` trava por 1 dia justamente para essa conferência sair em poucos dias; o `prod` trava por 90.

Um e-mail do alarme `BackupAtrasado` logo depois do primeiro deploy de cada ambiente é esperado: o alarme nasce sem dado nenhum, e sem dado conta como atraso. Ele volta a OK com o primeiro backup (em `prod`, às 03:07 seguintes ao merge).

Os comandos usam a credencial temporária do dono na conta 255235818791 (sa-east-1). O bucket de cada ambiente é a saída `BucketDoBackup` da pilha `financial-<ambiente>-dados`, e os alarmes ficam na `financial-<ambiente>-app`.

## Checklist

- [ ] `dev`, a partir de 2026-11-01 (quatro dias depois do primeiro backup, de 2026-10-28): `aws s3api list-object-versions --bucket <bucket do dev> --prefix diario/` não mostra versões criadas há mais de 3 dias. Se mostrar, a regra não expira versões travadas depois do prazo: abrir ticket para trocar a regra (ou apagar por script) antes que o `prod` acumule
- [ ] `prod`, no dia seguinte ao merge do ticket 64: existe `diario/<data>.zip` e `aws s3api get-object-retention` dá `COMPLIANCE` com prazo de 90 dias; baixar o zip e abrir os CSVs e o `manifesto.json`
- [ ] Alarmes: a inscrição do tópico `Avisos` já confirmada (ticket 29); `aws cloudwatch set-alarm-state --alarm-name <alarme BackupAtrasado> --state-value ALARM --state-reason teste` entrega o e-mail (o mesmo para o `BackupFalhou`)
- [ ] `prod`, 92 dias depois do primeiro backup de `prod` (anote a data no item do dia seguinte ao merge): as versões dos primeiros dias sumiram, inclusive as sobrescritas no mesmo dia (versão antiga travada por 90 dias)
- [ ] Resultado em `## Answer`
