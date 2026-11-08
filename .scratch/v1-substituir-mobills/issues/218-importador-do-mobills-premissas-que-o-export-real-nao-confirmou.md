# Importador do Mobills: premissas que o export real não confirmou

Type: task
Status: ready-for-human
Blocked by: —
Skills: `run` (o dono confere no app e na planilha; HITL: só ele tem o Mobills)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #568
Origem: [ticket 92](92-rodar-o-importador-nos-exports-reais.md) (a rodada nos exports reais não deu como confirmar estes pontos)

## O que fazer

- **Separador de várias tags**: das 12.590 linhas do geral real, 618 têm tag e nenhuma traz mais de uma (sem `,` `;` `|` ou `/`). A vírgula de `_tags` em `leitura.py` segue aposta. O dono olha no app se alguma transação tem duas tags e, se tiver, como o export a traz.
- **Centavo da divisão das parcelas**: comparar uma parcela gerada com a do Mobills (a parcela gerada copia o valor da última que veio).
- **Parcelas de parcelamento de cartão sem fatura em mês já exportado**: contar quantas ficam na conta enquanto o parcelamento fica no cartão (a aba `Parcelamentos sem cartão` tem 135 parcelamentos, mas a contagem desse caso não saiu).

## Checklist

- [x] Tags: confirmado ou corrigido o separador
- [x] Centavo da divisão conferido num parcelamento
- [ ] Contagem das parcelas de cartão sem fatura em mês exportado gravada em `## Answer`

## Answer

- **Tags**: o dono conferiu no app e nenhuma transação tem mais de uma tag. O separador (vírgula) continua sem exemplo real, mas não há o que corrigir.
- **Centavo da divisão**: o dono conferiu e a parcela gerada bate com a do Mobills.
- **Parcelas de cartão sem fatura em mês exportado**: pendente. O dono apontou, na aba `Parcelamentos sem cartão`, 12 que são pagamentos mensais ou débitos automáticos da conta e não compra parcelada: Aluguel, Buenos Aires, Imposto de renda, IR, Lavanderia, pagamento buffet, pagamento decoração, PECE-Poli, Reembolso vistoria carro, Samuel Fotografia, Seguro residencial, Título de capitalização. O restante parece ser cartão de crédito, sem conferência; falta confirmar nas faturas em PDF do dono e gravar a contagem aqui.
