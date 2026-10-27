# Lançamento sem internet: fila e envio em lote

Type: task
Status: ready-for-agent
Blocked by: 32
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #87
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 42, 44, 46, 47, 48, 49, 50, 51, 52, 53

## O que construir

Sem internet, criar, editar, excluir e confirmar lançamentos funciona: o lançamento fica no aparelho como não enviado (⏳), conta no saldo local e sobe sozinho quando a internet volta, sem duplicar ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)).

## Checklist

- [ ] Camada de dados do aparelho como único ponto de leitura e escrita das telas: cache da última resposta de cada tela ("atualizado às 14:32"), pacote para lançar e fila de não enviados
- [ ] Chamada de envio em lote que recebe as ações na ordem e devolve um resultado por ação (aceita, conflito, recusada com motivo ou descartada por exclusão); reenviar nunca duplica; recusa não trava as seguintes
- [ ] Fila sobe ao abrir ou voltar ao app, pelo botão "Enviar agora" e, no Android, em segundo plano; ⏳ nas listas, contagem na Hoje e destaque depois de 24 h
- [ ] Recusa aparece como "não enviado: <motivo>" para corrigir ou descartar; telas de configuração mostram o botão desativado com "precisa de internet"
- [ ] Testes de navegador com a rede desligada e religada: lançar offline, ⏳, envio sem duplicar e recusa com motivo
- [ ] Verificações do projeto rodando e PR aberto para `main`
