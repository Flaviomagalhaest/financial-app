# Parcelamento: criar

Type: task
Status: resolved
Blocked by: 37, 43
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #100
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 95, 96, 97, 98, 45, 105

## O que construir

O casal lança uma compra ou dívida em N parcelas, no cartão ou em boleto, também sem internet; cada parcela é um lançamento e a compra parcelada não é.

## Checklist

- [x] Informar valor total ou da parcela; os centavos que sobram vão para a 1ª parcela
- [x] No cartão, cada parcela conta no mês da fatura em que cai e nasce automática; em boleto, parcelamento fora do cartão
- [x] Sem internet vai como um pedido só, gerado pelo servidor
- [x] Testes de API com divisão de centavos e viradas de fatura
- [x] Verificações do projeto rodando e PR aberto para `main`
- [x] Parcela automática não pede confirmação (ticket 43): gravar `lancamentos.automatico = true` na parcela, que já a tira de `GET /api/contas-da-semana` e do `atrasado` (ticket 44), e fazer a tarefa diária (`realizar_automaticos` em `backend/app/recorrencias.py`, que hoje só acha os previstos com `recorrencia_id`) realizar também as parcelas, com a `origem` do parcelamento

## Notas

- API em `backend/app/parcelamentos.py`: `POST /api/parcelamentos` (id gerado no aparelho; o reenvio devolve o gravado com 200 e completa a geração que parou) e `GET /api/parcelamentos`. Entra `valor_total_centavos` ou `valor_da_parcela_centavos` (um dos dois), `parcelas` de 2 a `maximoDeParcelas` (420, em `config/valores-iniciais.json`), `data` (no cartão, a da compra; fora dele, a da 1ª parcela) e `automatico`. Só despesa. O cartão sem dia de fechamento é recusado antes de gravar, porque não há como escolher a fatura da 1ª parcela.
- Cada parcela é um lançamento com `parcelamento_id`, `parcela` e `parcelas` (o total, lido do parcelamento), id `uuid5(parcelamento, número)` e `parcelamentos.geradas` até onde gerou, em lotes de uma transação (migrations 0037 a 0041, backup na versão 14 com o conversor da 13). No cartão, todas têm a data da compra e a parcela n cai n - 1 faturas depois da fatura da compra (`faturas.mes_da_parcela`), e a redistribuição pelas datas do cartão e a edição da data mantêm essa distância.
- Automático: no cartão sempre (`automatico: false` é 422); fora dele, opcional. A 1ª parcela e a do boleto viram realizadas na data; a parcela n > 1 do cartão, quando a fatura de antes fecha. A realização dos automáticos das duas regras saiu de `recorrencias.py` para `backend/app/automaticos.py`, com a `origem` "o parcelamento <descrição>", e a tarefa diária também completa a geração que parou no meio.
- Sem internet: o lote saiu de `lancamentos.py` para `backend/app/lote.py` e ganhou a ação `criar_parcelamento`, cujo resultado aceito traz o `parcelamento`. A planilha da exportação escreve a parcela como o Mobills ("Geladeira (3/10)").
- Pendências: a tela e a fila do app no [ticket 93](93-parcelamento-criar-pela-tela-e-sem-internet.md); as regras provisórias (quando a parcela do cartão vira realizada, a recusa do `automatico: false`, o limite de 420, só despesa e o boleto no passado) são decisão do dono no [94](94-parcelamento-regras-provisorias.md). Notas gravadas nos [35](35-teste-nos-dois-celulares.md) (conferir no DSQL), [42](42-jornada-completa-do-lancamento-rapido.md) (o parcelado é do 93), [47](47-parcelamento-editar-regerar-excluir.md), [48](48-antecipar-e-quitar.md), [56](56-limite-comprometido-do-cartao.md), [68](68-importador-do-mobills-parcelamentos-pendentes-e-ajustes.md) (o formato do backup) e [87](87-recorrencia-com-inicio-no-passado.md).
- O ticket 38 entrou antes na `main` com a migration 0036 e a versão 13 do backup: o 46 renumerou as suas e foi para a 14. O PR aberto do ticket 45 também cria a 0036 e a versão 13: quem for mesclado depois renumera e sobe a versão, com o conversor.
