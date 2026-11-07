# Edição em lote na compra com partes

Type: decision
Status: resolved
Blocked by: —
Skills: `grilling`, `domain-modeling` (HITL: decisão do dono); depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #353
Origem: [ticket 137](137-partes-da-compra.md): a compra com partes não tem categoria nem tag próprias (ADR 0022), e a edição em lote mexe na categoria e na tag do lançamento

## O que decidir

O ticket 137 deixou a compra com partes de fora da edição em lote: a prévia conta quantas ficaram de fora (`com_partes_fora`) e o lote não as muda, nem as partes. Sem isso, a edição em lote daria categoria própria a uma compra com partes. Falta decidir o que o lote faz nelas:

- **Aplicar em cada parte** ("acrescentar Casa" acrescenta em todas as partes; "trocar Mercado por Feira" troca nas partes que têm Mercado), com o desfazer guardando as partes de antes;
- **Aplicar só nas partes que a busca achou** (o filtro por categoria, tag ou pessoa já diz quais partes batem);
- **Continuar de fora**, com a prévia dizendo por quê.

A tela da edição em lote ainda não mostra o `com_partes_fora`.

## Checklist

- [x] Decidir o comportamento (e o desfazer)
- [x] Gravar no glossário ou na ADR 0022
- [x] Implementar com teste de API e de navegador; a prévia mostra o que muda (nada fica de fora)

## Decisão (07/11)

O dono aceitou, numa rodada de `grilling`:

- **Em quais partes**: a mudança vale em cada parte; quando a linha veio de uma busca com filtro de categoria, tag ou pessoa, só nas partes que ela achou, mesmo que também marcada à mão. "Substituir" segue a mesma regra.
- **Parcelamento com partes**: mudam as partes dele e as de cada parcela; a parcela com partes próprias ("só esta") muda nas dela e segue alterada à mão. A compra parcelada conta como uma.
- **Recorrência**: a ocorrência muda nas partes como no "só este"; a regra não muda.
- **Recusa**: a parte que ficaria sem categoria recusa o lote inteiro, dizendo quantas partes.
- **Desfazer**: guarda a classificação de antes de cada parte e a devolve. A implementação pula a compra inteira, não só a parte, quando as partes mudaram depois: a escolha volta ao dono no [ticket 191](191-desfazer-do-lote-nas-partes.md).
- **Prévia**: sai `com_partes_fora`; entra `partes_que_mudam`, a amostra mostra cada parte que muda, e `trocam_de_item` conta também as partes.
- Gravado na [ADR 0022](../../../docs/adr/0022-partes-da-compra.md) e em **Edição em lote** no glossário. O estorno de uma parte acompanha a parte. O desfazer guarda as partes em `edicao_em_lote_partes` (formato do backup 34).

## Pendências

- [Ticket 191](191-desfazer-do-lote-nas-partes.md): desfazer por parte ou por compra, e o débito técnico achado na revisão.
