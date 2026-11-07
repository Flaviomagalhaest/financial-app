# Limite do estorno de uma parte do parcelamento: regra ou parcelas reais

Type: decision
Status: resolved
Blocked by: —
Skills: `grilling`, `domain-modeling` (HITL: decisão do dono); apoio: `implement`, `tdd` se a decisão mudar o código
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #382
Origem: revisão do [ticket 160](160-estorno-de-todas-de-uma-parte-do-parcelamento.md): o que a implementação escolheu por conta própria

## O que decidir

O 160 entregou o estorno de todas as parcelas de uma parte do parcelamento com estas escolhas provisórias:

- **Soma da parte pela regra**: o limite é a soma da parte nas parcelas *da regra* (o total do parcelamento dividido em parcelas e cada uma na proporção das partes de agora, `somas_nas_parcelas`), não a soma das partes gravadas nas parcelas (`lancamento_partes`). É a mesma escolha do limite do parcelamento inteiro, que usa `valor_total_centavos`. Ela diverge quando uma parcela mudou "só nesta" (valor ou partes) ou quando "esta e as próximas" mudou a proporção só de uma parcela em diante: as anteriores ficam com a divisão antiga, mas o limite e a trava da correção usam a nova em todas. Alternativa: somar o que as parcelas gravaram (e calcular as que ainda não foram geradas pela regra).
- **Item do estorno**: o estorno herda só a escolha explícita de item da parte do parcelamento (`item_categoria_id`). Sem escolha, conta no item do mês pela regra de onde conta (o item sozinho ou "a escolher"), como o estorno de todas sem partes. Na compra à vista, o estorno de parte leva também o item em que a parte conta sozinha.
- **Ligação no aparelho pela posição**: para mostrar o que resta sem internet, o app liga a parte da parcela à do parcelamento pela posição. O servidor liga pelo id (`id_na_parcela`). A parcela com partes próprias com o mesmo número de partes pode mostrar um restante que o servidor depois recusa.
- **Estorno de todas anterior à divisão**: fica ligado ao parcelamento inteiro, com a classificação que tinha, e pode ser editado; não acompanha mais nada (como na compra à vista, ticket 159).

## Checklist

- [x] Dono decide cada item acima (manter ou mudar)
- [x] O que mudar vira ticket de implementação ou entra aqui, com testes
- [x] ADR 0016 (adendo do 160) acompanha a decisão

## Resposta

Decidido com o dono (grilling):

- **Soma da parte pela regra**: mantida. É a mesma conta do limite do parcelamento inteiro (`valor_total_centavos`), que também ignora o "só nesta". O limite barra erro de digitação, não fecha a contabilidade, e as parcelas ainda não geradas precisariam da regra de todo jeito. Se um dia mudar, mudam os dois limites juntos.
- **Item do estorno**: mantido. Só a escolha explícita de item da parte é herdada. No parcelamento, cada parcela cai num mês, e o item em que a parte conta sozinha pode mudar de um mês para outro.
- **Ligação no aparelho pela posição**: muda. O aparelho passa a ligar pelo mesmo `uuid5` do servidor, com tabela compartilhada (ADR 0018). Isso é o [ticket 190](190-aparelho-liga-a-parte-da-parcela-pelo-id.md).
- **Estorno de todas anterior à divisão**: mantido, como na compra à vista (ticket 159).

O ADR 0016 ganhou o adendo do 161.
