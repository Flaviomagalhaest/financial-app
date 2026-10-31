# Parcelamento: criar pela tela e sem internet

Type: task
Status: resolved
Blocked by: 42
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` na folha de detalhes
Modelo recomendado: Opus
Effort recomendado: high
Issue: #185
Origem: [ticket 46](46-parcelamento-criar.md) (só a API existe: `POST /api/parcelamentos`, a ação `criar_parcelamento` no lote e a tarefa diária); spec da v1, histórias de usuário 45, 95, 96, 98

## O que construir

O casal marca "Parcelado" na folha de detalhes do novo lançamento e o parcelamento sobe com a fila, também sem internet, como um pedido só ([ticket 21](21-sincronizacao-offline-e-conflitos.md): o servidor gera as parcelas ao receber).

## Checklist

- [x] Folha de detalhes do [ticket 42](42-jornada-completa-do-lancamento-rapido.md): "Parcelado" com o número de parcelas, valor total ou da parcela, e "automático" só fora do cartão (no cartão o parcelamento já é automático e a API recusa `automatico: false`)
- [x] A fila do app (`web/src/dados/fila.ts`) guarda o pedido como um item só, com a ação `criar_parcelamento` de `POST /api/lancamentos/lote` (`backend/app/lote.py`), e mostra "Geladeira, 10x, não enviado" até o envio; o resultado aceito traz o `parcelamento`, e as parcelas chegam na leitura dos lançamentos
- [x] Reenvio do mesmo id com dados diferentes: hoje devolve o gravado sem comparar, como a recorrência; seguir a decisão do [ticket 86](86-recorrencia-criar-pela-tela-e-sem-internet.md) (ficou assim: o aparelho não edita a regra não enviada, então nunca reenvia o id com outros dados)
- [x] Seguir o caminho da recorrência na fila (`criar_recorrencia` em `web/src/dados/fila.ts`, `useRecorrenciasNaoEnviadas` e a releitura dos lançamentos em `enviarAgora`), e tornar o `ItemDaFila` (`web/src/dados/armazem.ts`) uma união pela `acao`: com o parcelamento, são três tipos de pedido checados em `acoesDo`, `remeterLote`, `naTela` e no `AvisoDaFila` (revisão do ticket 86)
- [x] Tempo do lote: cada `criar_parcelamento` gera as parcelas em transações próprias (até 420 parcelas); conferir se um lote cheio (100 ações) com parcelamentos longos cabe no tempo limite da Lambda e da HTTP API, ou limitar os parcelamentos por lote
- [x] Testes de API, se a ação mudar, e de navegador do fluxo, online e sem internet
- [x] Verificações do projeto rodando e PR aberto para `main`
- [x] Corrigir e excluir o parcelamento pela tela (ticket 47: `PATCH` e `DELETE /api/parcelamentos/{id}`, hoje só a API): o aviso 409 `AvisoDeRealizadas` mostra as realizadas que mudam ou saem e o pedido repete com `confirmar_realizadas`; a lista mostra a marca `alterada_a_mao` da parcela editada à mão; decidir se corrigir e excluir sem internet entram na fila ou pedem rede (o lote só aceita `criar_parcelamento`)

## Answer

- **A tela**: "Repete? Parcelado" só na despesa nova (a API só parcela despesa). Pede o número de parcelas e se o valor digitado é o total (sem juros) ou o da parcela (com juros), e mostra a divisão ("3x: R$ 33,34 na 1ª e R$ 33,33 nas outras"). "Automático" só aparece fora do cartão: no cartão o campo nem vai, e o servidor o liga. A data vira "Data da compra" (no cartão) ou "Primeira parcela", e a situação e a fatura saem da folha. O aviso de planejamento conta a 1ª parcela. A divisão que o app repete do servidor ganhou a tabela `tabelas-de-teste/divisao-das-parcelas.json` (ADR 0018).
- **A fila**: `ItemDaFila` virou uma união pela `acao` (`ItemDeLancamento`, e `ItemDeRegra` = recorrência ou parcelamento), com `deLancamento` para separar. O parcelamento sobe como um item só (`criar_parcelamento`), aparece em "Parcelamentos não enviados" ("Fogão, 10x, não enviado") e conta no aviso da Hoje ("1 lançamento e 1 parcelamento não enviados"). Ele se descarta como a recorrência: só enquanto com certeza não está no servidor. Quando o envio aceita um parcelamento, o app lê de novo os lançamentos, a Hoje e os parcelamentos.
- **Reenvio do mesmo id com outros dados**: fica como na recorrência (ticket 86). A API devolve o gravado sem comparar, e o aparelho não edita o parcelamento não enviado, então nunca reenvia o id com outros dados.
- **Tempo do lote**: o app limita a soma das parcelas dos parcelamentos de um lote a `maximoDeParcelas` (420), e o que passar disso vai no lote seguinte. O primeiro item vai sempre, então um parcelamento de 420 parcelas sobe sozinho. No Postgres local, 420 parcelas com 5 categorias e 5 tags levam cerca de 0,9 s. No DSQL ninguém mediu: ficou no [ticket 35](35-teste-nos-dois-celulares.md). Se a Lambda passar dos 29 s, o reenvio continua a geração de onde parou (o `gravar` devolve o gravado e o `gerar_as_parcelas` completa), e a tarefa diária também completa. A API não mudou e não ganhou teste novo.
- **Corrigir e excluir pela tela** (`#/parcelamento/<id>`, aberto pelo "⋯" de uma parcela no Histórico): os dois **precisam de internet** e não entram na fila, como a ADR 0011 já manda para mudanças de regras; sem rede, os botões ficam desligados. A correção manda só o que mudou. O 409 vira a lista das realizadas que mudam ou saem, com "Corrigir mesmo assim" (repete com `confirmar_realizadas`). A exclusão pede confirmação e avisa que as realizadas também saem. Depois de cada uma, o app lê de novo os lançamentos, as contas, a Hoje e os parcelamentos. No Histórico, a parcela mostra o número ("03/10") e "alterada à mão".
- **Parcelamento descartado no meio do envio**: se o envio já tinha saído, o parcelamento chega ao servidor mesmo assim. As parcelas aparecem na próxima leitura e se excluem pela tela, então isso não ficou pendente.

## Pendências

- Tempo de um lote com um parcelamento de 420 parcelas no DSQL: no [ticket 35](35-teste-nos-dois-celulares.md).
- O envio do service worker não lê de novo os lançamentos depois de uma regra aceita: o item do [ticket 96](96-recorrencia-mudar-pela-tela-e-sem-internet.md) agora fala também do parcelamento.
- A escolha do item do planejamento e a tag nova na correção, e abrir a tela sem internet sem ter lido o parcelamento antes: no [ticket 118](118-parcelamento-acabamentos-da-tela-de-correcao.md).
- Com o Postgres local cheio de rodadas, o envio da fila espera atrás das leituras compartilhadas (cada uma com até 10 s) e os testes de navegador falham sem nada ter subido: nota no [ticket 109](109-testes-de-navegador-sob-cpu-saturada.md).
