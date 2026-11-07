# Exclusão da recorrência criada falha de vez em quando no teste de navegador

Type: task
Status: claimed
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`, `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #502
Origem: [ticket 187](../../v1-substituir-mobills/issues/187-conta-em-todas-vai-para-o-parcelamento.md): CI do PR #499 (job `verificar`, 1ª execução, run 42390957792; verde ao reexecutar). O PR só mudou o backend do parcelamento.

## O problema

`web/e2e/recorrencia-mudar.spec.ts:234` ("a recorrência criada que talvez já esteja no servidor se exclui em vez de se descartar") estourou os 90 s no clique em "Excluir" da região "Recorrências não enviadas": o botão estava "not stable" e foi "detached from the DOM" a cada nova tentativa. A suspeita é a lista sendo redesenhada sem parar enquanto a fila tenta enviar. O vídeo e o trace ficaram no artefato `testes-com-navegador` daquela execução.

## Checklist

- [ ] Reproduzir (o teste repetido, ou com a CPU saturada como no ticket 109)
- [ ] Achar a causa (teste ou tela) e corrigir, sem desligar o teste
- [ ] Verificações do projeto e PR para `main`
