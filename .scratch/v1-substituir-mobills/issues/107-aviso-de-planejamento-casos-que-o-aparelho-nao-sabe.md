# Aviso de planejamento: casos que o aparelho ainda não sabe

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #209
Origem: [ticket 52](52-aviso-de-planejamento-ao-lancar.md): casos que o aviso de planejamento deixou de fora ou trata de forma aproximada, achados na implementação e na revisão

## O que construir

O aviso de planejamento (`web/src/dados/aviso.ts`, `useAvisoDePlanejamento` em `web/src/dados/index.ts`, `web/src/lancamentos/AvisoDePlanejamento.tsx`) acertando também estes casos, com teste de tabela ou de navegador para cada um.

## Checklist

- [ ] **Criar enviado sem resposta**: o item da fila com `talvezNoServidor` pode já estar no servidor. Se o planejamento guardado foi lido depois de ele chegar, o aviso o conta duas vezes até a fila sair. Hoje `contagensNoAparelho` soma todo item da fila sobre o planejamento guardado
- [ ] **Cartão arquivado num lançamento não enviado**: `GET /api/cartoes` não traz os arquivados. A compra não enviada num cartão arquivado conta, no aparelho, pelo mês da data, e não pela fatura
- [ ] **Mês sem planejamento guardado**: ao abrir, o app guarda o planejamento do mês anterior, deste e do próximo. O previsto com data mais longe, lançado sem internet, mostra "o planejamento de <mês> não está no aparelho". Decidir se basta ou se o aparelho guarda mais meses
- [ ] **Receita**: os textos do item de receita ("Faltam R$ X para o planejado", "R$ X acima do planejado", "Chega ao planejado") não têm teste
- [ ] **Transferência com categoria** conta no planejamento (história 67), mas a tela de transferência (`TelaDeTransferencia.tsx`) não mostra o aviso. Ela grava direto na API e já precisa de internet
- [ ] Verificações do projeto rodando e PR aberto para `main`
