# Edição com a resposta perdida não sobe ao reabrir e a exclusão seguinte vira conflito

Type: task
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #406
Origem: falha de `web/e2e/lancamentos.spec.ts` ("cria, edita e exclui um lançamento simples e o vê na lista") no CI do PR do [ticket 164](164-guardar-lancamento-por-lancamento-e-reler-so-o-que-mudou.md). Reproduzido também com o código da `main`.

## O problema

Num lançamento já no servidor (versão 1), a pessoa edita e o envio chega ao servidor, que grava a versão 2, mas a resposta não volta ao aparelho (o teste perdia ao recarregar logo depois de salvar). A edição fica na fila sobre a versão 1. Ao reabrir o app:

- a fila não sobe ao abrir: no experimento, a edição só foi enviada uns 3 s depois, na `main` mais de 10 s, e só porque a exclusão a substituiu;
- a pessoa exclui o lançamento, e a exclusão entra no lugar da edição levando a base dela (`atual.base`, versão 1, em `enfileirarExcluir`, `web/src/dados/fila.ts`);
- o servidor responde `conflito` ("alterado depois da sua versão"), e a linha fica com "⚠ conflito: sua mudança espera decisão": um conflito com a própria edição do aparelho.

Para reproduzir: em `lancamentos.spec.ts`, antes de salvar a edição, faça `page.route("**/api/lancamentos/lote")` deixar o primeiro pedido chegar ao servidor (`rota.fetch()`) e depois cair (`rota.abort("connectionreset")`); recarregue e exclua.

O teste do 164 passou a esperar a edição subir antes de recarregar, que é o que ele quer conferir. O defeito do app continua.

## O que investigar

- Por que o envio ao abrir (`iniciarEnvioAutomatico`) não sobe a fila logo, depois de uma resposta perdida: a trava, o estado "sem resposta" de `rede.ts`, ou outra coisa.
- Se a exclusão sobre uma edição talvez já gravada deve ir sobre a versão que essa edição gerou, como o criar talvez gravado (`talvezNoServidor`), ou se o servidor deve tratar como não conflito a mudança que traz os valores que ele já tem.

## Checklist

- [x] Teste de navegador com a resposta da edição perdida, o `reload` e a exclusão: o lançamento sai sem conflito
- [x] A fila sobe ao reabrir, sem esperar a pessoa mexer de novo

## Resolução

A causa é a base da mudança seguinte, não o envio ao abrir. A edição que saía sem resposta ficava na fila igual, sobre a versão 1, sem marca de que talvez já estivesse gravada (só o criar tinha a marca). A próxima mudança do lançamento entrava no lugar dela levando essa base: a exclusão ia com a versão 1, e a edição seguinte mudava de novo um campo que o servidor já tinha na versão 2. Os dois voltavam como conflito com a própria edição do aparelho. Quando a fila subia antes de a pessoa mexer, o reenvio da edição era aceito (o servidor aceita a mudança igual ao que tem) e a exclusão ia sobre a versão 2. Por isso o teste do 164 falhava só às vezes: era corrida entre o envio ao abrir e o clique.

A fila sobe, sim, ao abrir (`iniciarEnvioAutomatico`): o envio saiu 0,1 s depois de recarregar, e 1 s com a CPU 8 vezes mais lenta. A demora de 3 s a 10 s vista no CI não se reproduziu: a trava e o "sem resposta" de `rede.ts` não seguram o envio ao abrir. Ela não é a causa: o conflito vem sempre que a pessoa mexe antes de a fila subir, mesmo com o envio rápido.

A correção (`web/src/dados/fila.ts`): antes de o lote sair, a edição e a confirmação guardam as ações que levam (`enviadoSemResposta`, `guardarOEnviado`). Isso cobre também a página que fecha com o pedido no caminho, quando o `fetch` nem chega a falhar. Se o item muda antes da resposta, o envio seguinte reenvia primeiro essas ações. Aceitas, a mudança nova sobe sobre a versão que elas geraram. Recusadas ou em conflito, ela sobe sobre a base em que foi feita, e o servidor decide sobre ela. Qualquer resposta apaga o que ficou guardado.

Testes: `web/e2e/resposta-perdida.spec.ts`. Outra aba segura a trava da fila para a mudança entrar antes do envio, e os testes cobrem a exclusão (resposta perdida e recarga no meio), a edição de novo e a fila subindo sozinha ao abrir.

Pendência: [ticket 173](173-criar-com-a-pagina-fechada-no-meio-do-envio.md), o mesmo caso para o criar.
