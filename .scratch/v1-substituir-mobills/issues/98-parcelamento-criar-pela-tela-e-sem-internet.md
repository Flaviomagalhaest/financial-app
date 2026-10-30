# Parcelamento: criar pela tela e sem internet

Type: task
Status: ready-for-agent
Blocked by: 42
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` na folha de detalhes
Modelo recomendado: Opus
Effort recomendado: high
Issue: #185
Origem: [ticket 46](46-parcelamento-criar.md) (só a API existe: `POST /api/parcelamentos`, a ação `criar_parcelamento` no lote e a tarefa diária); spec da v1, histórias de usuário 45, 95, 96, 98

## O que construir

O casal marca "Parcelado" na folha de detalhes do novo lançamento e o parcelamento sobe com a fila, também sem internet, como um pedido só ([ticket 21](21-sincronizacao-offline-e-conflitos.md): o servidor gera as parcelas ao receber).

## Checklist

- [ ] Folha de detalhes do [ticket 42](42-jornada-completa-do-lancamento-rapido.md): "Parcelado" com o número de parcelas, valor total ou da parcela, e "automático" só fora do cartão (no cartão o parcelamento já é automático e a API recusa `automatico: false`)
- [ ] A fila do app (`web/src/dados/fila.ts`) guarda o pedido como um item só, com a ação `criar_parcelamento` de `POST /api/lancamentos/lote` (`backend/app/lote.py`), e mostra "Geladeira, 10x, não enviado" até o envio; o resultado aceito traz o `parcelamento`, e as parcelas chegam na leitura dos lançamentos
- [ ] Reenvio do mesmo id com dados diferentes: hoje devolve o gravado sem comparar, como a recorrência; seguir a decisão do [ticket 86](86-recorrencia-criar-pela-tela-e-sem-internet.md)
- [ ] Tempo do lote: cada `criar_parcelamento` gera as parcelas em transações próprias (até 420 parcelas); conferir se um lote cheio (100 ações) com parcelamentos longos cabe no tempo limite da Lambda e da HTTP API, ou limitar os parcelamentos por lote
- [ ] Testes de API, se a ação mudar, e de navegador do fluxo, online e sem internet
- [ ] Verificações do projeto rodando e PR aberto para `main`
- [ ] Corrigir e excluir o parcelamento pela tela (ticket 47: `PATCH` e `DELETE /api/parcelamentos/{id}`, hoje só a API): o aviso 409 `AvisoDeRealizadas` mostra as realizadas que mudam ou saem e o pedido repete com `confirmar_realizadas`; a lista mostra a marca `alterada_a_mao` da parcela editada à mão; decidir se corrigir e excluir sem internet entram na fila ou pedem rede (o lote só aceita `criar_parcelamento`)
