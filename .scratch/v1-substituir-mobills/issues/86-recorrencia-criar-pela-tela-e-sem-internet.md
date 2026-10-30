# Recorrência: criar pela tela e sem internet

Type: task
Status: resolved
Blocked by: 42
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` na folha de detalhes
Modelo recomendado: Opus
Effort recomendado: high
Issue: #167
Origem: [ticket 44](44-recorrencia-criar.md) (só a API existe: `POST /api/recorrencias` e a tarefa diária); spec da v1, histórias de usuário 45, 87, 88

## O que construir

O casal marca "Repete? recorrente" na folha de detalhes do novo lançamento e a regra sobe com a fila, também sem internet, como um pedido só ([ticket 21](21-sincronizacao-offline-e-conflitos.md): o servidor gera os previstos ao receber).

## Checklist

- [x] Folha de detalhes do [ticket 42](42-jornada-completa-do-lancamento-rapido.md): "Repete?" com recorrente ativado, a cada N semanas ou meses, sem fim, até uma data ou por N vezes, valor fixo ou estimado e "automático" só no fixo
- [x] Ação `criar_recorrencia` em `POST /api/lancamentos/lote` (`backend/app/lancamentos.py`, `Acao`), com o resultado trazendo a regra gravada; a fila do app (`web/src/dados/fila.ts`) guarda o pedido como um item só e mostra "Luz, todo mês, não enviado" até o envio
- [x] Reenvio do mesmo id com dados diferentes: hoje `POST /api/recorrencias` devolve a gravada com 200 sem comparar (como o `_criar` do lançamento); decidir se vira conflito (ADR 0011) ou fica assim
- [x] Testes de API da ação no lote e de navegador do fluxo, online e sem internet
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

- **Reenvio do mesmo id com outros dados fica como está**: `POST /api/recorrencias` e a ação `criar_recorrencia` devolvem a regra gravada, sem comparar e sem conflito. O aparelho nunca manda isso: a recorrência não enviada não se edita, só se descarta, e cada novo lançamento tem um id novo. A regra não tem versão em que basear um conflito (o da ADR 0011 é por campo do lançamento), e quem muda a regra é o `PATCH` (ticket 96). Se a outra pessoa mudar a regra entre o envio sem resposta e o reenvio, o reenvio devolve a regra já mudada. É fácil de reverter, então não virou ADR.
- **A tela**: "Repete? Recorrente" só no lançamento novo. A data vira "Primeira vez" (o `inicio`), e a situação e a fatura saem da folha, porque quem decide é a regra. O padrão é todo mês, sem fim e estimado, e "automático" só aparece no fixo. Salvar põe a regra na fila como um item só, e os previstos chegam na leitura dos lançamentos depois que ela sobe (o app relê a lista quando o envio aceita uma recorrência).
- **Descartar**: só a recorrência que com certeza não está no servidor (nunca saiu do aparelho ou foi recusada). A que ficou sem resposta mostra que talvez já esteja lá e sobe quando a rede voltar.

## Pendências

- Excluir pela fila a recorrência que talvez já esteja no servidor (envio sem resposta, ou "Descartar" no meio do envio) e reler a lista e a Hoje depois de um envio do service worker: no [ticket 96](96-recorrencia-mudar-pela-tela-e-sem-internet.md).
- A 1ª ocorrência de hoje nasce prevista, mesmo vinda do novo lançamento: pergunta do [ticket 87](87-recorrencia-com-inicio-no-passado.md).
- A fila agora tem dois tipos de pedido (lançamento e recorrência) e o parcelamento será o terceiro: tornar o `ItemDaFila` uma união pela `acao` no [ticket 98](98-parcelamento-criar-pela-tela-e-sem-internet.md).
