# Recorrência: o mês pulado dentro do trecho que o fim tirou reaparece ao reabrir

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #224
Origem: [ticket 95 (recorrência)](95-recorrencia-reabrir-e-reagendar-sem-buraco.md): limite conhecido da escolha "trazer de volta as excluídas pela regra"

## O que construir

O casal que pulou um mês e depois encerrou a recorrência antes dele não vê esse mês voltar quando reabrir o fim.

## O problema

O 95 distingue o previsto que o fim (ou o horizonte) tirou do que o casal pulou pelo número da ocorrência: o fim faz `recorrencias.geradas` recuar até antes do primeiro previsto que saiu, e a geração só traz de volta o excluído com número acima de `geradas`. O mês pulado de antes tem número já gerado, então não volta. O furo: o mês pulado que cai no trecho que o fim tirou (número maior que o novo `geradas`) é, para a geração, igual aos que o fim tirou, e reaparece como previsto ao reabrir.

Exemplo: sem fim, o casal pula a ocorrência 12; depois encerra na 10 (`geradas` recua para 10); reabre (`ate: null`) e a 12 volta.

A mesma coisa pelo horizonte, sem fim nenhum e mais fácil de acontecer: o casal pula a 15 (com `geradas` em 24) e reagenda para 3 em 3 meses; `geradas` recua para 8 e a 15 volta quando o horizonte a alcança.

## Checklist

- [ ] Testes de API dos dois exemplos (pular a 12, encerrar na 10, reabrir; pular a 15, reagendar, esperar o horizonte): o pulado segue excluído
- [ ] Marcar na exclusão quem a fez, a regra ou uma pessoa: coluna nova em `lancamentos` (migration, conversor do backup e sua versão) ou outro jeito que não use o número; a geração só reviva a que a regra tirou
- [ ] O que o casal excluiu depois de realizado já fica de fora (a geração só revive `situacao = 'previsto'`); conferir que continua
