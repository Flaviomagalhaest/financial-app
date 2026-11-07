# Cópia local da pessoa e do item do estorno ligado

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #492
Origem: [ticket 191](191-item-e-pessoa-do-estorno-acompanham-a-compra.md), revisão (07/11): o servidor e a tela (pessoa só leitura) estão prontos; a cópia local não.

## O que construir

- O estorno ligado guardado no aparelho acompanha a pessoa da compra, da parte, da parcela ou do parcelamento quando ela muda sem internet, como o servidor (`acompanhar_estornos`).
- O estorno de todas sem partes acompanha a escolha de item do parcelamento na cópia local.
- Hoje o app só pré-preenche a pessoa na criação (`preencherEstorno`) e trava os botões (`pessoaTravada`); o caminho da fila (`web/src/dados/index.ts`) ainda repassa a pessoa do cliente.

## Checklist

- [ ] Teste: a mudança de pessoa da compra aparece no estorno ligado sem internet
- [ ] Teste: o estorno de todas sem partes mostra o item do parcelamento sem internet
- [ ] Implementar na cópia local
