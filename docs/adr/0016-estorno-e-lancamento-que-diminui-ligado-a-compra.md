---
status: accepted
---

# O estorno é um lançamento de despesa que diminui, ligado à compra original

O estorno (crédito de uma compra devolvida) é uma linha de `lancamentos` com `tipo` `despesa` e a coluna `estorno_de` apontando para a compra original. O valor fica positivo, como em toda despesa, e quem soma despesas trata o estorno com sinal contrário: a fatura, o mês, a categoria, a tag e o item do planejamento descontam o que ele devolve, no mês da fatura em que ele aparece. Ele leva as mesmas categorias e tags da compra, vai para um cartão, e a soma dos estornos de uma compra não passa do valor dela. O ajuste de fatura, que não é lançamento, segue a [ADR 0008](0008-ajuste-de-fatura-fica-na-fatura.md): uma coluna `ajuste_centavos` na tabela `faturas`.

## Considered Options

- **`tipo` `receita` com a categoria da compra**: a regra "categoria de despesa num lançamento de despesa" impediria as mesmas categorias, e o estorno apareceria em receitas e na sobra do mês como se fosse dinheiro novo.
- **Valor negativo na despesa**: a coluna tem `CHECK (valor_centavos > 0)`, e o DSQL não altera restrições (ADR 0009); trocar a restrição pediria refazer a tabela e quebraria o backup, como na ADR 0014.
- **Tabela própria de estornos**: todo lugar que lista ou soma lançamentos (fila do aparelho, busca, planilha, planejamento) teria de juntar duas tabelas.

## Consequences

- Toda soma de despesa precisa do sinal: `VALOR_COM_SINAL` em `app/lancamentos.py` serve às somas do cartão e do mês, e o planejamento tem o seu `CASE`. Quem criar uma soma nova de despesa trata `estorno_de`.
- O saldo da conta não muda, porque o estorno só existe no cartão e o saldo do cartão não é de uma conta.
- A planilha exporta o estorno com o sinal contrário ao da compra (crédito).
- O backup sobe para a versão 14 (`estorno_de` no lançamento e `ajuste_centavos` na fatura).

## Adendo (ticket 94)

Revisto com o dono no [ticket 94](../../.scratch/v1-substituir-mobills/issues/94-conferir-as-regras-de-estorno-e-ajuste.md):

- As categorias e tags do estorno acompanham as da compra quando ela muda, inclusive as arquivadas. A compra com estorno não pode ser excluída: exclui-se o estorno antes.
- O **estorno avulso** é um crédito no cartão sem compra ligada (a correção de centavos de uma loja), com categoria, tags e pessoa opcionais e sem o limite do valor da compra. Sem categoria, conta só na fatura e no mês.
- Na compra com partes ([ADR 0022](0022-partes-da-compra.md)), o estorno é de uma parte e vai até o valor dela. Na compra parcelada, o estorno é de uma parcela ou de todas: o de todas é um estorno só, ligado ao parcelamento (ou à parte dele), até a soma das parcelas menos o já estornado, e conta inteiro no mês da fatura em que aparece.

## Adendo (ticket 133)

O estorno não tem categorias, tags nem item do planejamento próprios, mas as linhas continuam gravadas nele: `acompanhar_estornos` (`app/lancamentos.py`) as copia da compra ao criar o estorno e toda vez que a compra muda (edição, correção de parcelamento, reajuste de recorrência; a edição em lote já leva o estorno junto). Assim as somas (fatura, mês, categoria, tag, item, busca, planilha) seguem lendo as mesmas tabelas, sem juntar o estorno à compra em cada consulta. Quem criar um caminho novo que mude a classificação de uma compra chama `acompanhar_estornos`. O servidor ignora a classificação que o cliente manda no estorno novo. A compra com estorno não se exclui (422), por qualquer caminho; as regras que tiram parcela ou ocorrência com estorno seguem o adendo do ticket 148.

## Adendo (ticket 135)

O **estorno avulso** é a mesma linha de `lancamentos` (`tipo` `despesa`, no cartão) sem `estorno_de` e com a coluna `estorno_avulso` verdadeira. A marca é uma coluna própria (nulo vale falso) porque `estorno_de` vazio já é a compra comum, e o DSQL não altera restrições (ADR 0009). O backup sobe para a versão 26. Quem soma despesas trata o crédito como "`estorno_de` preenchido **ou** `estorno_avulso`": `VALOR_COM_SINAL`, o `CASE` do planejamento (`app/planejamento.py`) e a planilha (`app/exportacao.py`). No app, `eEstorno` (`lancamentos/apresentacao.tsx`) é o mesmo teste, e a soma do aparelho (`dados/aviso.ts`, `dados/busca.ts`) o repete. Chega pela mesma `POST /api/lancamentos` e pela mesma fila, com `estorno_avulso: true`; a categoria é a única obrigação que cai (`categoria_ids` vazio só vale no avulso, na criação e na edição). Cai na fatura aberta ou fechada e nunca na paga (a regra da ADR 0021 vale para ele sem código próprio). Sem categoria, conta só no total da fatura e do mês; com categoria, também na categoria, na tag e no item do planejamento. Não leva o limite do valor de uma compra. `acompanhar_estornos` só mexe nos ligados a uma compra, então o avulso guarda a classificação que o casal deu.

## Adendo (ticket 138)

O estorno de uma parte e o de todas as parcelas são a mesma linha de `lancamentos`, com duas colunas novas (backup na versão 30; nulo vale "não é"):

- **Parte**: `estorno_de` aponta para a compra e `estorno_parte_id` para a parte. Na compra com partes, a parte é obrigatória; o estorno herda as categorias, as tags e o item dela (`acompanhar_estornos` segue a parte), e a soma dos estornos da parte não passa do valor dela, nem a de todos os estornos da compra do valor da compra. A parte que tem estorno não some nem encolhe abaixo do estornado, e as partes só se juntam sem estorno de parte. O estorno anterior à divisão da compra fica ligado à compra inteira, com a classificação que tinha.
- **Todas as parcelas**: `estorno_parcelamento_id` aponta para o parcelamento e `estorno_de` fica vazio. É um estorno só, até `valor_total_centavos` menos o já estornado (de cada parcela e de todas), com a classificação do parcelamento (`acompanhar_estornos_do_parcelamento`, chamado onde ela muda: correção e edição em lote). Conta inteiro no mês da fatura em que aparece e trava a exclusão do parcelamento. "O banco antecipa e depois estorna" é a quitação seguida do estorno de todas, sem atalho.

Quem soma despesas trata o crédito com `e_estorno()` (`app/partes.py`): `estorno_de` **ou** `estorno_parcelamento_id` **ou** `estorno_avulso`; no app, `eEstorno` (`lancamentos/apresentacao.tsx`) e as somas do aparelho repetem o teste. As decisões que ficaram provisórias estão no [ticket 159](../../.scratch/v1-substituir-mobills/issues/159-estorno-de-parte-e-de-parcelas-pendencias.md).

## Adendo (ticket 160)

No parcelamento com partes (ticket 139), o estorno de todas as parcelas é de uma parte dele: `estorno_parcelamento_id` aponta para o parcelamento e `estorno_parte_id` para a linha de `parcelamento_partes`. A parte é obrigatória, como na compra com partes. O estorno herda as categorias, as tags e a escolha de item da parte (`acompanhar_estornos_do_parcelamento` segue a parte). O limite é a soma da parte nas parcelas (cada parcela da regra dividida na proporção das partes, `somas_nas_parcelas`) menos o já estornado nela, no estorno de todas e no de cada parcela, na parte da parcela que veio dela (o id dela é `id_na_parcela(parcela, parte)`). O estorno de uma parcela também respeita esse limite. Na correção do parcelamento, a parte com estorno não sai, as partes não se juntam e a soma dela não fica abaixo do estornado. O estorno de todas anterior à divisão do parcelamento fica com a classificação que tinha, como na compra à vista. O app repete a soma da parte para mostrar o que ainda dá para estornar sem internet (ADR 0018, tabela `tabelas-de-teste/somas-das-partes.json`) e liga a parte da parcela à do parcelamento pela posição; quem decide é o servidor, pelo id.

## Adendo (ticket 148)

Decidido com o dono no [ticket 148](../../.scratch/v1-substituir-mobills/issues/148-parcela-com-estorno-quando-a-regra-a-tira.md): a regra nunca exclui o estorno junto (ele é um crédito que veio da fatura real), e o que acontece depende de quem pediu.

- **Correção do parcelamento** que tiraria uma parcela com estorno (menos parcelas, parcela que sai ou é pulada): recusa o pedido (422) antes de gravar, como a que encolhe abaixo da fatura paga. É a pessoa que corrige, então ela exclui o estorno e repete. Deixar a parcela ficaria além do total de parcelas.
- **Reajuste da recorrência**: o previsto com estorno fica como está por inteiro, como o mexido à mão, e o reajuste segue com os outros. Ele roda em lotes e pela tarefa diária, sem ninguém para ler uma recusa.
- **Exclusão da regra de recorrência**: o previsto com estorno fica, como o realizado e o atrasado; a exclusão nunca é recusada por ele.
- **Correção de fatura** que exclui a compra e o estorno dela: o servidor exclui os estornos antes das compras, qualquer que seja a ordem do pedido. A compra cujo estorno fica continua recusada, e a correção inteira volta (tudo ou nada).
- **Dado antigo**: o estorno desalinhado da compra (de antes do ticket 133, inclusive em backup restaurado) não ganha migração nem acerto na restauração; ele se acerta quando a compra mudar.

A implementação é o [ticket 188](../../.scratch/v1-substituir-mobills/issues/188-regras-que-tiram-parcela-ou-ocorrencia-com-estorno.md).

## Adendo (ticket 152)

Decidido com o dono no [ticket 152](../../.scratch/v1-substituir-mobills/issues/152-estorno-avulso-pendencias.md); a implementação é o [ticket 189](../../.scratch/v1-substituir-mobills/issues/189-estorno-avulso-item-fatura-e-testes.md):

- **Item do planejamento**: o avulso tem classificação própria, então a tela "Lançar crédito" pergunta o item como na compra, quando as categorias escolhidas têm dois ou mais itens no mês. "A escolher" na Hoje fica para o que chegar sem escolha. O estorno ligado continua sem escolha própria.
- **Devido negativo**: o servidor recusa (422) o avulso que deixaria o devido da fatura dele (saldo anterior + compras + ajuste, com os créditos) abaixo de zero. A conferência só roda ao salvar o avulso (criação e edição, inclusive a troca de data ou de fatura). Excluir ou mover compra, ajuste negativo e o estorno ligado (que já tem o teto da compra) não ganham trava: o cenário é raro, e a ADR 0021 segue sem saldo anterior negativo. O aparelho não confere: sem internet, o avulso sobe pela fila e a recusa aparece como qualquer recusa da fila.
- **Mês sem fatura**: "Lançar crédito" aparece em qualquer mês que não esteja pago, com ou sem fatura criada. A data decide a fatura, e ela nasce com as datas padrão (`garantir_fatura`), como na primeira compra.

## Adendo (ticket 161)

Decidido com o dono no [ticket 161](../../.scratch/v1-substituir-mobills/issues/161-limite-do-estorno-de-parte-do-parcelamento.md), sobre as escolhas do adendo do 160:

- **Limite da parte pela regra**: fica. A soma da parte é a das parcelas da regra (`somas_nas_parcelas`), não a das partes gravadas nas parcelas, como no limite do parcelamento inteiro (`valor_total_centavos`). A parcela mudada "só nesta" e a proporção mudada "esta e as próximas" não mexem no limite. O limite barra erro, não fecha a contabilidade. Se um dia passar a contar o gravado, os dois limites mudam juntos.
- **Item**: fica. O estorno de parte do parcelamento herda só a escolha explícita de item da parte. Sem ela, conta no item do mês pela regra de onde conta, porque cada parcela cai num mês.
- **Ligação no aparelho**: muda. O app liga a parte da parcela à do parcelamento pelo mesmo `id_na_parcela` (uuid5) do servidor, não pela posição, com tabela compartilhada (ADR 0018). A implementação é o [ticket 190](../../.scratch/v1-substituir-mobills/issues/190-aparelho-liga-a-parte-da-parcela-pelo-id.md). Até ela, vale o que o adendo do 160 descreve.
- **Estorno de todas anterior à divisão**: fica com a classificação que tinha, ligado ao parcelamento inteiro, como na compra à vista.
