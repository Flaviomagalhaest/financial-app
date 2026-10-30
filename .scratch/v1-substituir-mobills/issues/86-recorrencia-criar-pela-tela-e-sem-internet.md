# Recorrência: criar pela tela e sem internet

Type: task
Status: claimed
Blocked by: 42
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` na folha de detalhes
Modelo recomendado: Opus
Effort recomendado: high
Issue: #167
Origem: [ticket 44](44-recorrencia-criar.md) (só a API existe: `POST /api/recorrencias` e a tarefa diária); spec da v1, histórias de usuário 45, 87, 88

## O que construir

O casal marca "Repete? recorrente" na folha de detalhes do novo lançamento e a regra sobe com a fila, também sem internet, como um pedido só ([ticket 21](21-sincronizacao-offline-e-conflitos.md): o servidor gera os previstos ao receber).

## Checklist

- [ ] Folha de detalhes do [ticket 42](42-jornada-completa-do-lancamento-rapido.md): "Repete?" com recorrente ativado, a cada N semanas ou meses, sem fim, até uma data ou por N vezes, valor fixo ou estimado e "automático" só no fixo
- [ ] Ação `criar_recorrencia` em `POST /api/lancamentos/lote` (`backend/app/lancamentos.py`, `Acao`), com o resultado trazendo a regra gravada; a fila do app (`web/src/dados/fila.ts`) guarda o pedido como um item só e mostra "Luz, todo mês, não enviado" até o envio
- [ ] Reenvio do mesmo id com dados diferentes: hoje `POST /api/recorrencias` devolve a gravada com 200 sem comparar (como o `_criar` do lançamento); decidir se vira conflito (ADR 0011) ou fica assim
- [ ] Testes de API da ação no lote e de navegador do fluxo, online e sem internet
- [ ] Verificações do projeto rodando e PR aberto para `main`
