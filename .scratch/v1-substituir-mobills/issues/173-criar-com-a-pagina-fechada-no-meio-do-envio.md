# Criar com a página fechada no meio do envio e a exclusão seguinte

Type: task
Status: claimed
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

- [ ] Teste de navegador: criar com a recarga no meio do envio, excluir ao reabrir, e o lançamento sai do servidor
- [ ] A marca do criar não muda o planejamento nos envios que recebem resposta
