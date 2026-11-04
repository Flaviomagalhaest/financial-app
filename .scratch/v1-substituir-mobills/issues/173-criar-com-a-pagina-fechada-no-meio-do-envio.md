# Criar com a página fechada no meio do envio e a exclusão seguinte

Type: task
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #414
Origem: [ticket 169](169-edicao-com-a-resposta-perdida-e-a-exclusao-seguinte.md). Hipótese lida no código, nunca reproduzida.

## O problema

O criar que sai sem resposta só fica marcado como talvez gravado (`talvezNoServidor`, em `marcarSemResposta`, `web/src/dados/fila.ts`) quando o `fetch` falha. Se a página fecha ou recarrega com o pedido no caminho, o `fetch` não chega a falhar e a marca não é gravada, mas o servidor pode ter gravado o lançamento. Ao reabrir, a pessoa exclui antes de a fila subir: `enfileirarExcluir` acha um criar sem a marca e só o tira da fila. O lançamento ficaria no servidor e voltaria na próxima leitura.

O ticket 169 resolveu o mesmo caso para a edição e a confirmação, guardando o que elas levam antes de o lote sair (`guardarOEnviado`). O criar tem a marca com outro uso: o planejamento lido depois de `tentadoEm` já conta o criar talvez gravado, então marcar antes de enviar mudaria o que a tela mostra em todo envio.

## Para reproduzir

Em `web/e2e/resposta-perdida.spec.ts`, como no caso `"recarga"`: lance o lançamento com o lote deixado chegar ao servidor (`rota.fetch()`) e sem resposta, recarregue com a fila presa pela trava de outra aba e exclua. Confira na API se o lançamento ainda está lá.

## Checklist

- [x] Teste de navegador: criar com a recarga no meio do envio, excluir ao reabrir, e o lançamento sai do servidor
- [x] A marca do criar não muda o planejamento nos envios que recebem resposta

## Resolução

A recarga do ticket não reproduz: o navegador derruba o pedido ao recarregar, o `fetch` falha ainda na página e `marcarSemResposta` grava a marca (o teste `"recarga"` passa sem a correção). O caso real é a aba fechada ou o app morto pelo sistema, em que a página não vê a falha: o teste `"aba fechada"` ficou vermelho (o lançamento continuava no servidor) e verde com a correção.

A correção usa o mecanismo do ticket 169: `guardarOEnviado` guarda também o criar (`enviadoSemResposta`) antes de o lote sair, e `enfileirarExcluir` só tira da fila o criar sem essa guarda e sem `talvezNoServidor`. A exclusão sobe depois do criar reenviado (o servidor devolve o que já tinha) e o tira de lá. A marca que o planejamento lê (`talvezNoServidor`, `tentadoEm`) continua só na falha, então o envio que recebe resposta não muda o que a tela mostra. Em `aplicar`, o criar reenviado com a exclusão atrás conta como excluído no caminho.

Pendência: a regra tem o mesmo buraco com a aba fechada, no [ticket 181](181-regra-descartada-depois-da-pagina-fechada.md).
