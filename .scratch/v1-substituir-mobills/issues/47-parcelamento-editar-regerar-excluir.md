# Parcelamento: editar, regerar e excluir

Type: task
Status: resolved
Blocked by: 46
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #101
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 101, 102, 103, 104

## O que construir

O casal corrige um parcelamento errado sem refazer tudo.

## Checklist

- [x] Editar descrição, tags ou pessoa vale para todas as parcelas, inclusive as realizadas
- [x] Corrigir valor, número de parcelas ou data gera as parcelas de novo, com aviso quando uma realizada vai mudar; parcela editada à mão fica marcada e é preservada
- [x] Excluir o parcelamento inteiro
- [x] Testes de API
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Do [ticket 46](46-parcelamento-criar.md): as parcelas de um parcelamento são os lançamentos com o `parcelamento_id` dele; o id de cada uma é `uuid5(parcelamento, número)` e `parcelamentos.geradas` diz até que parcela já gerou. Ainda não há marca de alterado à mão no lançamento (a mesma falta do [45](45-recorrencia-mudar.md)). `PATCH` numa parcela do cartão já mantém a distância de n - 1 faturas (`faturas.mes_da_parcela`). A tabela `parcelamentos` não tem marca de exclusão. A regeração precisa recalcular a fatura das parcelas com a data nova e, na parcela automática, o `realiza_em`.
- API em `backend/app/parcelamentos.py`:
  - `PATCH /api/parcelamentos/{id}`: descrição, categorias, tags, pessoa e item (`item_categoria_id`) valem para todas as parcelas, as realizadas também, e a parcela editada à mão também as recebe. `valor_total_centavos` ou `valor_da_parcela_centavos` (um dos dois; o da parcela vale vezes o número de parcelas), `parcelas` e `data` refazem as parcelas; só o número de parcelas mantém o total. `confirmar_realizadas` (padrão `false`).
  - Se uma parcela realizada vai mudar (valor, data ou fatura) ou sair, a resposta é 409 `AvisoDeRealizadas` (`parcelas`: id, número, valor e data de antes e de depois, `sai`) e nada é gravado; o mesmo pedido com `confirmar_realizadas` muda. Previstas não pedem confirmação.
  - Parcela editada à mão: `lancamentos.alterada_a_mao`, calculado de `lancamento_campos` (campo `valor_centavos`, `data`, `conta_id` ou `fatura_mes` sem `origem`, isto é, mudado por uma pessoa, pelo `PATCH` do lançamento ou pela confirmação com ajuste). Sem coluna nova. A correção a preserva nessas quatro coisas; encolher o parcelamento além dela é 422.
  - A refeita grava com `registrar_mudancas(..., origem=origem(descricao))` e `subir_versao`, e a edição sem internet sobre a versão de antes recebe o 409 "O do parcelamento ...". Lotes de uma transação (`_por_lote`), como a recorrência; se parar no meio, repetir o `PATCH` continua. `geradas` passa a `min(geradas, parcelas)`.
  - A parcela excluída uma a uma não volta. A que saiu porque o parcelamento encolheu (excluída com número depois de `geradas`) volta se ele crescer.
  - A parcela automática que a data nova já alcançou se realiza no próprio `PATCH` (`automaticos.realizar_automaticos(url, parcelamento_id)`), como na criação.
  - `DELETE /api/parcelamentos/{id}` é idempotente (204): dá `geradas = parcelas` para a tarefa diária não gerar mais, exclui todas as parcelas em lotes (as realizadas e as editadas à mão também, o que tira a despesa do saldo) e apaga o parcelamento e as ligações dele.
- Sem migration e sem mudança no backup: a marca é calculada. O contrato ganhou `alterada_a_mao` no lançamento, `PATCH` e `DELETE` do parcelamento.
- Pendências gravadas: as regras provisórias deste ticket (só o número muda o total, a classificação sobre a parcela editada à mão, a exclusão com realizadas sem aviso, a realizada que vai para o futuro, trocar cartão ou conta, `automatico`) no [99](99-parcelamento-regras-provisorias.md); a tela, a marca na lista e a correção sem internet no [98](98-parcelamento-criar-pela-tela-e-sem-internet.md); a antecipação e a quitação sobre a marca de alterada à mão no [48](48-antecipar-e-quitar.md); conferir os lotes no DSQL no [35](35-teste-nos-dois-celulares.md); a correção que para no meio e a corrida com a tarefa diária no [102](102-parcelamento-correcao-interrompida-e-corrida.md).
- A correção só refaz a classificação que o pedido trouxe (descrição, categorias, tags, pessoa, item), para a descrição que uma pessoa corrigiu numa parcela só não voltar a cada correção de valor. Com parcelas editadas à mão, a soma das parcelas deixa de ser o `valor_total_centavos`, e os centavos que sobram seguem na 1ª parcela. Mudou também: `realizar_automaticos(url, parcelamento_id)`, `ALTERADA_A_MAO` em `lancamentos.py`, o glossário ("Parcela alterada à mão", "Correção do parcelamento"), o README e o ADR 0004.
