# Testes sem internet intermitentes no CI (saldo da conta e resposta perdida)

Type: task
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`, `run`
Modelo recomendado: Opus
Effort recomendado: high
Issue: #263
Origem: PR do [ticket 113](113-editar-enquanto-a-criacao-sobe-vira-conflito.md) (31/10). O CI dele falhou num teste que o PR não toca, e a `main` e outros PRs falham num teste vizinho do mesmo arquivo.

## O que falha

- `e2e/sem-internet.spec.ts:336` › "o saldo da conta conta os não enviados do aparelho (criar e excluir) com ⏳ e, ao enviar, fica igual ao do servidor": depois de lançar R$ 45,00 sem internet, o saldo mostra `-R$ 45,00 ⏳` em vez de `-R$ 46,00`, como se o saldo guardado da conta não contasse o R$ 1,00 enviado antes (o teste já tinha visto `-R$ 1,00` sem ⏳). CI: run 197 (PR do 113). Local, na `main` (b2c56b1), sem o 113: 2 de 5 com `--repeat-each=5`.
- `e2e/sem-internet.spec.ts:300` › "criado com a resposta perdida e depois editado ou excluído sem internet: a mudança não se perde": para no "Salvar" (linha 321) ou no `toContainText("− R$ 0,19")` (linha 322). CI: run 189 (`main`, merge do 110) e run 196 (PR do 61).

Só local, com o Postgres de `scripts/postgres-local.sh` já cheio de execuções anteriores (o CI sobe um banco novo a cada run):

- `e2e/lancamentos.spec.ts:134` › "contas: cria com saldo de abertura, renomeia e arquiva...": o botão "Desarquivar conta ..." não aparece depois de arquivar. 5 de 5 na `main` local, depois de umas 300 execuções do arquivo no mesmo banco; no começo da sessão passava.
- `e2e/busca.spec.ts:142` › "sem internet, a busca mostra o que o aparelho guarda...": 1 linha em vez de 2. Uma vez, na suíte inteira.

## Pistas

- Para o `:336`: o saldo guardado das contas é lido de novo depois do envio sem esperar (`void Promise.all(...)` em `enviarAgora`, `web/src/dados/index.ts`, ticket 81). Uma leitura das contas que começou antes de o lançamento subir pode ser guardada depois da leitura nova? A `comTrava("shared")` de `buscarEGuardar` deveria impedir isso; conferir também a leitura que a própria tela "Contas e categorias" faz ao abrir.
- Os dois locais podem ser só o volume de dados do banco local (muitas contas e lançamentos de teste): conferir com um banco novo antes de tratar como bug.

## Checklist

- [x] Reprodução determinística de cada falha do CI (atraso no `context.route`, como nos tickets 113 e 114)
- [x] Causa (app ou teste) e correção, com o teste vermelho antes
- [x] Os dois só locais conferidos num banco novo: bug, ou nota no README sobre limpar o banco local
- [x] `sem-internet.spec.ts` com `--repeat-each=5` sem falha
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

São três bugs do app e duas corridas dos testes (e um quarto bug, do acerto da fatura, apareceu no CI do PR). O volume do banco local só alargava a janela do `lancamentos.spec.ts:134`. Cada correção tem teste vermelho antes, determinístico, com `page.route`.

### `sem-internet.spec.ts:336` (saldo da conta): bug do app

O saldo do aparelho é o saldo guardado das contas mais o efeito da fila. Quando o lançamento sobe, o `aplicar` (`web/src/dados/fila.ts`) tira o item da fila e acerta a lista e a Hoje guardadas, mas o saldo guardado só mudava com a releitura de `/api/contas` que o `enviarAgora` dispara depois (ticket 81). Se a rede cai entre o lote e essa releitura, o saldo guardado fica sem o enviado. A sonda mostrou isso no CI: o teste via "-R$ 1,00" (guardado 0 + fila), o item saía da fila e a releitura saía 44 ms depois do lote, já sem internet.

A hipótese da `comTrava("shared")` não se confirmou: a trava exclusiva do envio impede que uma leitura velha das contas seja guardada depois do lote.

Correção: o `aplicar` acerta também o saldo guardado de `/api/contas` e `/api/contas?arquivadas=true` (`comOsEnviados`, em `saldo.ts`), na mesma transação que tira o item da fila, pela diferença entre como a lista guardada tinha e passa a ter o lançamento. A releitura continua, e traz o saldo do servidor. Teste: "a rede cai logo depois do envio, antes de o saldo ser lido de novo...", em que nenhuma leitura das contas chega depois do lote.

### `sem-internet.spec.ts:300` (resposta perdida): corrida do teste e bug do app

- **Teste.** O `rota.fetch()` do Playwright não respeita o `context.setOffline`: o lote do segundo `lancar`, ainda sem internet, passava pela rota e perdia a resposta ali. O `expect.poll(perdidas)` já valia antes de a rede voltar, e o envio de verdade ainda estava no caminho quando o teste desligava a rede e abria a edição. Agora a rota recusa o lote enquanto o teste está sem rede (`comRede`).
- **App.** Esse envio era aceito sem a lista guardada: a leitura dela no `enviarAgora` (ticket 90) falhava porque a rede ainda não tinha voltado de todo, e o lote saía logo depois. O `aplicar` tirava os itens da fila e eles sumiam do aparelho, o que dava o Histórico vazio ("não foi possível carregar os lançamentos") e a edição aberta em branco (R$ 0,09 e o Salvar desabilitado). Agora, se a lista não chega, o `enviarAgora` não envia e devolve `false`. Teste: "a rede volta, mas a lista não chega antes do envio...".

### `lancamentos.spec.ts:134` (só local): bug do app

As leituras de uma resposta correm juntas (a trava é `shared`), e a última a chegar era a guardada. A leitura que a tela "Contas e categorias" faz ao abrir pode sair antes do `PUT` de arquivar e chegar depois da releitura, e aí guarda a conta ainda não arquivada. No banco local cheio, o `GET /api/contas` demora mais e a janela cresce, daí o 5 de 5. Correção: o `buscarEGuardar` (`web/src/dados/index.ts`) numera as leituras e só guarda a resposta de uma que saiu depois da última guardada naquele caminho. O `manterOsDois` passou a guardar a lista por ele. Teste: "a leitura das contas que saiu antes de arquivar e chega depois não desfaz o arquivar".

### `busca.spec.ts:142` (só local, uma vez): corrida do teste

Falhou também num banco novo. O resultado online vem do `POST /api/busca` do servidor, e o teste desligava a rede antes de a tela terminar de ler e guardar a lista, as contas e as categorias criadas pela API, de onde sai a busca sem internet. Com o `abort` dessas leituras o teste ficou vermelho 3 de 3, com o mesmo sintoma. Agora ele espera as três leituras chegarem com o que a API criou.

### O banco local cheio

Numa segunda suíte no mesmo banco novo, `pessoa-e-repetido.spec.ts` e `favoritos.spec.ts` falharam também com o código da `main`: com uns 1.600 lançamentos do usuário de teste, o Histórico levou 6,1 s para mostrar o lançamento novo, e os testes esperam 5 s. Isso ficou no README ("Como testar": recriar o banco local antes de conferir uma falha intermitente), e a medida com o volume real foi para o [ticket 123](123-historico-com-o-volume-real.md).

### No CI do PR

- O teste novo "a rede volta, mas a lista não chega antes do envio" passou de 5 s no CI. Com os dados da suíte inteira, o envio espera a lista inteira chegar e ser gravada; cada leitura dela grava a lista toda no IndexedDB, uma de cada vez, e o Histórico sem internet lê atrás dessas gravações. No banco local cheio falhou 5 de 25, sempre com a fila e a lista guardadas certas, e com 15 s nas duas checagens passou 15 de 15. A medida disso está no [ticket 123](123-historico-com-o-volume-real.md).
- `cartoes-cadastro.spec.ts:73` falhou uma vez, com o seletor da fatura em "Outro mês…". É um bug do formulário de acerto da fatura (`SecaoDeCartoes.tsx`), que já estava na `main`. Logo depois do login, o app guarda as faturas do cartão recém-criado, ainda vazias. O formulário abria com elas, escolhia "Outro mês…" e não voltava atrás quando a leitura nova trazia a fatura. Agora a escolha automática segue a lista mais nova até a pessoa mexer no formulário. Teste: "o acerto da fatura abre na fatura que nasceu, mesmo com as faturas guardadas de antes da primeira compra" (vermelho 3 de 3 antes).
- Numa suíte local, `aviso-de-planejamento.spec.ts:270` falhou: o `perdidas++` contava o lote quando ele chegava à rota, antes de o `rota.fetch()` gravar no servidor, e o teste lia o planejamento antes da gravação. Com um atraso antes do `fetch` ficou vermelho 2 de 2; agora o teste espera o servidor gravar (`gravou`). Os outros testes com `perdidas++` antes do `fetch` (contas da semana, parcelamento, recorrência, sem internet) esperam a tela mostrar a perda, que só aparece depois do `abort`, e não precisam disso.

### Verificação

- Sonda do `:336`, 50 rodadas antes da correção: 6 falhas; depois: 0 em 40. `:300`, 40 rodadas: 3 falhas antes, 0 depois. `busca.spec.ts:142`: 10 de 10.
- `sem-internet.spec.ts --repeat-each=5`: 65 de 65. `npm run typecheck` e `npm run build` passando. Suíte inteira num banco novo: 178 de 179, e a que falhou foi o `busca.spec.ts:142`, corrigido depois (10 de 10).

### Pendências

- [Ticket 122](122-envio-em-segundo-plano-sem-a-lista-guardada.md): o envio em segundo plano (service worker) não tem as duas garantias novas (não subir sem a lista guardada e não deixar a leitura velha trocar a guardada), sem teste para o `sync` (o CDP já o dispara num teste do arquivo).
- [Ticket 123](123-historico-com-o-volume-real.md): medir o Histórico no aparelho com o volume real (a lista inteira na tela).
