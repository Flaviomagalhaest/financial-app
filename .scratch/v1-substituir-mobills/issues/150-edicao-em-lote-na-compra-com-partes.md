# Edição em lote na compra com partes

Type: decision
Status: ready-for-human
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

- [ ] Decidir o comportamento (e o desfazer)
- [ ] Gravar no glossário ou na ADR 0022
- [ ] Implementar com teste de API e de navegador; a prévia mostra o que ficou de fora
