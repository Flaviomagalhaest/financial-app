# Exclusão da recorrência criada falha de vez em quando no teste de navegador

Type: task
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`, `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #502
Origem: [ticket 187](../../v1-substituir-mobills/issues/187-conta-em-todas-vai-para-o-parcelamento.md): CI do PR #499 (job `verificar`, 1ª execução, run 42390957792; verde ao reexecutar). O PR só mudou o backend do parcelamento.

## O problema

`web/e2e/recorrencia-mudar.spec.ts:234` ("a recorrência criada que talvez já esteja no servidor se exclui em vez de se descartar") estourou os 90 s no clique em "Excluir" da região "Recorrências não enviadas": o botão estava "not stable" e foi "detached from the DOM" a cada nova tentativa. A suspeita é a lista sendo redesenhada sem parar enquanto a fila tenta enviar. O vídeo e o trace ficaram no artefato `testes-com-navegador` daquela execução.

## Checklist

- [x] Reproduzir (o teste repetido, ou com a CPU saturada como no ticket 109)
- [x] Achar a causa (teste ou tela) e corrigir, sem desligar o teste
- [x] Verificações do projeto e PR para `main`

## Resultado

Com 4 núcleos saturados e `--repeat-each`, o teste falhou em 1 de cada 2 a 3 execuções, mas na última linha (`linha(page, descricao)` com contagem 0 no Histórico), não no clique em "Excluir". **Causa (teste):** a exclusão da regra deixa a ocorrência de hoje como realizada (`excluir_regra`; a de valor estimado já nasce realizada), então o Histórico a mostra depois da releitura. A asserção só passava na janela em que a fila já esvaziou e a lista ainda escondia os previstos de hoje em diante. **Correção:** os dois testes (`talvez já esteja` e `descartada no meio do envio`) conferem agora, pela API, que não sobra previsto da regra (`previstosNoServidor`). Ver pendência abaixo.

## Pendência

O sintoma original (clique em "Excluir" estourando 90 s, botão "detached") não apareceu em ~45 execuções sob carga; a suspeita da lista redesenhada sem parar segue sem prova. Se voltar, o trace do artefato `testes-com-navegador` é o ponto de partida; reabrir este ticket.
