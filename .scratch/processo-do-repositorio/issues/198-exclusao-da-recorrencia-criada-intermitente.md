# Exclusão da recorrência criada falha de vez em quando no teste de navegador

Type: task
Status: ready-for-human
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

## Reaberto (ticket 196)

O sintoma original voltou no CI do PR #517 (job `verificar`, run 42417245960, 1ª execução). O PR só mudou o backend do parcelamento. `web/e2e/recorrencia-mudar.spec.ts:245` estourou os 90 s em `criadas.getByRole("button", { name: `Excluir ${descricao}` }).click()`: o botão estava "visible, enabled and stable" e foi "detached from the DOM", a cada nova tentativa. O vídeo e o trace estão no artefato `testes-com-navegador` dessa execução (id 13592578663).

- [ ] Reproduzir o clique em "Excluir" com o botão saindo da página (trace do artefato acima)
- [ ] Achar a causa (teste ou tela) e corrigir, sem desligar o teste
- [ ] Verificações do projeto e PR para `main`

## Diagnóstico da reabertura (sem causa provada)

Laço montado: Postgres local, `npm ci`, e `npx playwright test e2e/recorrencia-mudar.spec.ts -g "talvez já esteja" --repeat-each=N --trace off` com 4 núcleos saturados. Resultado: 25/25 verdes (2 min), nenhum clique em "Excluir" destacado.

Hipótese testada e **falsificada**: um reenvio entre `perder = false` e o clique sobe a recorrência, a região some e o "Excluir" fica destacado para sempre. Alarguei a janela de propósito (espera de 8 s e de 13 s após `perder = false`, acima do ping de 10 s de `/api/saude`): o teste passou nas duas. Lista e chaves (`key={r.id}`) são estáveis, então o redesenho da fila não remonta o `<li>`.

Sem laço vermelho não há correção honesta. Próximo passo, que precisa do dono: baixar o trace do artefato `testes-com-navegador` (id 13592578663, run 42417245960) e ver o que mudou no DOM no instante do clique; só com isso dá para formular outra hipótese.

Voltou no CI do PR #572 (2026-11-09, job `verificar`, run 42536784292, 1ª execução), que só mudou o backend do importador do Mobills: mesmo `recorrencia-mudar.spec.ts:245`, mesmo clique em "Excluir" da região "Recorrências não enviadas", botão "detached from the DOM" a cada tentativa até os 90 s. 340 dos 341 testes passaram. Trace e vídeo no artefato `testes-com-navegador` (id 13639619855) dessa execução, uma segunda fonte para o primeiro item abaixo.

- [ ] Dono: anexar/ler o trace do artefato e dizer o que a região fazia no instante do clique
- [ ] Reproduzir com esse dado, corrigir sem desligar o teste, verificações e PR
