# Recorrência: mudar, pular e encerrar pela tela e sem internet

Type: task
Status: resolved
Blocked by: 86
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Opus
Effort recomendado: high
Issue: #177
Origem: [ticket 45](45-recorrencia-mudar.md) (só a API existe: `PATCH` e `DELETE /api/recorrencias/{id}`); spec da v1, histórias de usuário 90, 91, 92, 93

## O que construir

O casal muda, pula e encerra uma recorrência na tela, e o pedido sobe com a fila quando não há internet.

## Checklist

- [x] No previsto de uma recorrência: "Só este mês" (edição comum do lançamento, que o marca como alterado à mão), "Daqui para frente" (`PATCH /api/recorrencias/{id}` com `a_partir_da_ocorrencia` = a `ocorrencia` do previsto), "Pular este mês" (excluir o previsto) e "Encerrar" (`ate` ou `vezes`)
- [x] Excluir a recorrência inteira (`DELETE /api/recorrencias/{id}`): avisar que o atrasado e o realizado ficam
- [x] Ações `alterar_recorrencia` e `excluir_recorrencia` em `POST /api/lancamentos/lote` (`backend/app/lancamentos.py`, `Acao`), e a fila do app (`web/src/dados/fila.ts`) guarda cada pedido como um item só
- [x] Mostrar na tela de conflito "O da regra <origem>" (a `origem` já vem no 409)
- [x] Alterar a recorrência não tem versão: duas pessoas mudando a regra ao mesmo tempo ficam com a última a chegar; decidir se isso basta (ADR 0011)
- [x] Recorrência criada no aparelho que talvez já esteja no servidor (envio sem resposta, ou "Descartar" tocado no meio do envio): hoje ela não se descarta e, se descartada no meio do envio, fica no servidor com os previstos; com `excluir_recorrencia` na fila, oferecer "Excluir" no lugar de "Descartar" (do [ticket 86](86-recorrencia-criar-pela-tela-e-sem-internet.md))
- [x] Depois de uma ação de recorrência (ou, desde o ticket 98, de um parcelamento) aceita, o app relê `/api/lancamentos` e `/api/hoje` só quando o envio sai da tela (`enviarAgora` em `web/src/dados/index.ts`); o envio do service worker (`segundoPlano.ts`) não relê, e a tela só se acerta ao voltar para o app (do ticket 86)
- [x] Testes de API das ações no lote e de navegador do fluxo, online e sem internet
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

- **Sem internet, pela fila** (decisão do dono nesta sessão, [ADR 0020](../../../docs/adr/0020-mudanca-da-recorrencia-vai-pela-fila.md), que abre a exceção na ADR 0011): "Daqui para frente", "Encerrar" e "Excluir a recorrência" entram na fila, cada mudança como um item (`alterar_recorrencia`, com id próprio, ou `excluir_recorrencia`, com o da regra), e o servidor reajusta ou tira os previstos ao receber. "Só este mês" e "Pular este mês" são a edição e a exclusão do previsto, como já eram. O aparelho não repete a regra: mostra a regra com a mudança por cima e esconde só os previstos que o fim ou a exclusão tiram; o valor novo dos previstos vem do servidor.
- **A tela**: o "⋯" de um lançamento da recorrência no Histórico abre `#/recorrencia/<lançamento>`, com a ocorrência dele como `a_partir_da_ocorrencia`. "Encerrar depois desta vez" manda `vezes` = a ocorrência; "Encerrar nessa data" manda `ate`. Mudar o calendário manda sempre o `inicio` (a data desta vez que a tela mostra), para a regra mostrada até o envio ser a que o servidor grava. Excluir avisa que o atrasado e o realizado ficam. O Histórico mostra "Mudanças de recorrência não enviadas" ("Luz: valor, não enviado") e a Hoje conta "mudança de recorrência" no aviso.
- **Regra sem versão**: não basta o último a chegar. A ação leva em `antes` o que a tela mostrava nos campos mudados (o fim conta como um campo só), e o servidor recusa ("a regra mudou depois (valor): confira e mude de novo") se outra mudança mexeu depois no mesmo campo; campos diferentes se mesclam e a mudança igual passa. A recusada não vale na tela até ser descartada. Reenviada depois de um envio sem resposta, a mudança vai sem `antes`, para não se recusar à toa. O `PATCH` sem `antes` segue com o último a chegar, e o app não o usa.
- **"O da regra <origem>"** na tela de conflito já existia; um teste de navegador cobre a edição sem internet de um previsto que a regra mudou depois.
- **Recorrência criada que talvez já esteja no servidor**: ganha "Excluir" no lugar de "Descartar" (a exclusão toma o lugar do criar na fila). A descartada no meio do envio é excluída do servidor logo depois que o envio volta aceito, e também quando ele fica sem resposta.
- **Releitura**: depois de qualquer regra aceita, a tela e agora também o service worker leem de novo os lançamentos, a Hoje, as recorrências e os parcelamentos (`RELIDAS_DEPOIS_DE_REGRA` em `web/src/dados/fila.ts`); um teste dispara o `sync` pelo CDP e vê a lista mudar sem a página ler nada.
- **Achado no caminho**: excluir a recorrência que ainda não começou dava erro (o fim de ontem ficava antes do início); agora o fim fica no início.
- **Tempo do lote**: criar, mudar e excluir recorrência contam os previstos até o horizonte no mesmo teto do parcelamento (`maximoDeParcelas` por lote).
- **Aceito como está**: a mudança de recorrência descartada no meio do envio pode valer no servidor mesmo assim, como a edição de um lançamento; a releitura depois do envio mostra a regra como ficou.

## Pendências

- Escolha do item do planejamento e tag nova na tela da recorrência, e os seletores repetidos com a tela do parcelamento: [ticket 120](120-recorrencia-acabamentos-da-tela.md).
