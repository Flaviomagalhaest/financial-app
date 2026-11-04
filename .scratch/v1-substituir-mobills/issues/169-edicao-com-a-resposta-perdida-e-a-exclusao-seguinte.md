# Edição com a resposta perdida não sobe ao reabrir e a exclusão seguinte vira conflito

Type: task
Status: claimed
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

- [ ] Teste de navegador com a resposta da edição perdida, o `reload` e a exclusão: o lançamento sai sem conflito
- [ ] A fila sobe ao reabrir, sem esperar a pessoa mexer de novo
