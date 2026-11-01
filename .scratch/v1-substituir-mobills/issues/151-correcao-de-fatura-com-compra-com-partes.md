# Correção de fatura com compra com partes

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #354
Origem: [ticket 137](137-partes-da-compra.md): a soma das partes é o valor da compra (ADR 0022), e a correção de fatura paga muda só o valor

## O que construir

Na correção de fatura paga (`#/cartoes/<cartão>/<mês>`, "Corrigir fatura"), mudar o valor de uma compra com partes volta recusado ("as partes somam X centavos e a compra, Y"), porque o formulário manda só `valor_centavos` e as partes deixam de somar o valor. A correção precisa acertar as partes junto (por exemplo, a diferença na última parte, como a tela de lançar faz com "o que falta da compra") ou abrir a edição das partes.

## Checklist

- [ ] Decidir na tela como a diferença se divide entre as partes (a última parte, como na tela de lançar)
- [ ] `compras_editadas` leva as partes acertadas
- [ ] Teste de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Desde o 140, a ocorrência da recorrência com partes divide as partes de novo quando só o valor muda (`editar` em `backend/app/lancamentos.py`), e a correção de fatura já funciona para ela; falta a compra à vista (e a parcela, quando o 139 chegar).
