# Lançamento sem internet: fila e envio em lote

Type: task
Status: resolved
Blocked by: 32
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #87
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 42, 44, 46, 47, 48, 49, 50, 51, 52, 53

## O que construir

Sem internet, criar, editar, excluir e confirmar lançamentos funciona: o lançamento fica no aparelho como não enviado (⏳), conta no saldo local e sobe sozinho quando a internet volta, sem duplicar ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)).

## Checklist

- [x] Camada de dados do aparelho como único ponto de leitura e escrita das telas: cache da última resposta de cada tela ("atualizado às 14:32"), pacote para lançar e fila de não enviados
- [x] Chamada de envio em lote que recebe as ações na ordem e devolve um resultado por ação (aceita, conflito, recusada com motivo ou descartada por exclusão); reenviar nunca duplica; recusa não trava as seguintes
- [x] Fila sobe ao abrir ou voltar ao app, pelo botão "Enviar agora" e, no Android, em segundo plano; ⏳ nas listas, contagem na Hoje e destaque depois de 24 h
- [x] Recusa aparece como "não enviado: <motivo>" para corrigir ou descartar; telas de configuração mostram o botão desativado com "precisa de internet"
- [x] Testes de navegador com a rede desligada e religada: lançar offline, ⏳, envio sem duplicar e recusa com motivo
- [x] `contarNaoEnviados` em `web/src/App.tsx` conta a fila de verdade, para "Sair" pedir confirmação com não enviados (ticket 30), com teste de navegador do aviso
- [x] Verificações do projeto rodando e PR aberto para `main`
- [x] Trocar as chamadas diretas à API de `TelaDeLancamento` e `ListaDeLancamentos` (ticket 32) pela camada de dados do aparelho, que hoje só mostra "Sem internet" ao salvar ou excluir
- [x] Confirmar sem internet entra na fila (ticket 43): passou para o [ticket 83](83-confirmar-previsto-sem-internet-pela-fila.md)

## Notas da implementação

- **Camada de dados**: `web/src/dados/` (`armazem.ts` com o IndexedDB `financial-app-dados`, `fila.ts` sem React, `index.ts` com os hooks das telas). Leituras de lançamentos, contas (também com as arquivadas) e categorias guardam a última resposta; as escritas de lançamento vão pela fila. As escritas de contas e categorias (`TelaDeContasECategorias`, ticket 74) e a exportação seguem direto na API, porque precisam de internet: sem rede, a tela de contas e categorias desativa tudo com "precisa de internet".
- **Fila**: no máximo uma mudança por lançamento (criar seguido de editar continua criar; excluir o que com certeza não subiu só o tira da fila). Um criar enviado sem resposta fica marcado como talvez gravado: a edição depois dele sobe como criar + editar, e a exclusão sobe de verdade. A revisão do item protege o que mudou enquanto o lote subia. Uma trava (Web Locks) separa o envio, exclusivo, das leituras, compartilhadas, entre abas e o service worker.
- **Lote**: `POST /api/lancamentos/lote`, até 100 ações (`LIMITE_DO_LOTE`, também em `fila.ts`), cada uma pelas rotas de um lançamento só, na sua transação (com a nova tentativa do ticket 75). 422 vira `recusada` com o motivo, 404 vira `descartada`, banco fora do ar ou disputa perdida derrubam o lote (o aparelho reenvia), outro erro vira `recusada` "erro no servidor". O `conflito` está no contrato e o aparelho o trata como recusa marcada "conflito" até o ticket 34. Se o servidor recusar o formato do lote inteiro (422), o aparelho manda um a um.
- **Segundo plano**: o `vite.config.ts` empacota `src/dados/segundoPlano.ts` com o `rolldown` (agora em `devDependencies`) dentro do `service-worker.js`, que atende o `sync` `enviar-fila`. Para renovar o token sem a tela, as chamadas diretas ao Cognito saíram de `login/cognito.ts` para `login/renovacao.ts` (sem a biblioteca do SRP), com `tokenEmSegundoPlano`.
- **Reserva**: numa sessão só, a reserva (`Status: claimed`) foi commitada na própria branch de trabalho, sem o PR `reserva-33` separado.
- **Pendências**: [81](81-saldo-conta-os-nao-enviados.md) (saldo contando os não enviados, história 46), [82](82-rede-que-nao-responde-e-tempo-limite.md) (rede que não responde e tempo limite), [83](83-confirmar-previsto-sem-internet-pela-fila.md) (confirmar previsto pela fila, depois do ticket 43); linhas novas nos tickets [35](35-teste-nos-dois-celulares.md) (segundo plano num Android de verdade) e [52](52-aviso-de-planejamento-ao-lancar.md) (aviso sobre a resposta guardada e a fila).
