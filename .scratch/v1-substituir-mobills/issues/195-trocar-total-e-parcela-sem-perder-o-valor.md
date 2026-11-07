# Trocar entre o total e o da parcela sem perder o valor digitado

Type: task
Status: resolved
Blocked by: —
Skills: `grilling` (HITL: decisão do dono); depois `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #488
Origem: [ticket 158](158-mudar-as-partes-pela-tela-do-parcelamento.md): revisão de spec

## O que decidir

Na tela do parcelamento, o botão "O total / O da parcela" põe no campo o valor que o parcelamento gravado tem naquele modo, e descarta o valor que a pessoa acabou de digitar; as partes (ticket 158) se convertem para esse valor. Já era assim antes do 158.

- Trocar de modo deve converter o valor digitado (o total digitado vira o da parcela, dividido pelo número de parcelas do formulário, e o contrário), ou continua voltando ao gravado?

## Checklist

- [x] Dono decide: converter o digitado
- [x] Implementar, com teste de navegador (escrito, não rodado na sessão: sem backend); verificações do projeto e PR para `main`
