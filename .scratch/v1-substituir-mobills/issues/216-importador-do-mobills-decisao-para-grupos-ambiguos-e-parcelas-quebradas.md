# Importador do Mobills: decisão para grupos ambíguos e parcelas quebradas

Type: task
Status: resolved
Blocked by: —
Skills: `grilling` (HITL: o dono diz o que decide em cada aba), `domain-modeling` se surgir termo novo; depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #566
Origem: [ticket 92](92-rodar-o-importador-nos-exports-reais.md) (o dono rodou o importador nos exports reais e disse que as abas `Grupos ambíguos` e `Parcelas quebradas` precisam de uma coluna de decisão; hoje só informam)

## O que construir

Nos exports reais, a aba `Grupos ambíguos` tem 26 linhas (13 grupos) e a `Parcelas quebradas` tem 342 sequências (216 com cartão, 126 sem; 337 com parcela faltando e 16 com parcela duplicada no mês). As duas só informam: o ticket 18 manda o grupo e a sequência "para a revisão" sem dizer o que o dono decide.

Sessão de `grilling` com o dono para fechar:

- o que ele decide em cada linha (nos grupos ambíguos: casar de outro jeito, separar? nas parcelas quebradas: gerar as que faltam, deixar avulsas, juntar a duplicada?);
- se os 342 são esperados (compras lançadas como parcela em meses fora dos exports, parcelas de 2026-09 em diante que ainda não chegaram) ou sinal de problema em `parcelas.py`: 79 têm falta só no fim, 101 só no começo e 157 nos dois lados;
- como a decisão volta ao importador (colunas na própria aba, como as outras abas, mantidas nas rodadas seguintes).

## Checklist

- [x] Decisões por aba registradas (grilling)
- [x] Coluna de decisão nas abas e o importador lê e mantém a decisão
- [x] Teste: a decisão muda o resultado do cruzamento ou do parcelamento e sobrevive a uma nova rodada
- [x] Se os 342 forem sinal de problema, diagnosticar `parcelas.py` num ticket à parte (diagnóstico aqui; correção no ticket 219)

## Answer

Grilling com o dono em 2026-11-08. Antes das perguntas, o agente rodou o importador nos exports reais (`data/historic/`, fora do git) e só contou.

### Fatos

- **Grupos ambíguos (13)**: em todos, as linhas do geral diferem só na situação (`Paga` contra `Pendente`), nunca nas tags. Em 10, há 1 linha de fatura para 2 do geral; em 9 desses a fatura casava com a `Pendente` (vem antes na ordem do export) e a `Paga` sobrava como débito realizado **na conta**: a compra contada duas vezes. Os outros 3 são 2×2.
- **Credicard depois de cancelado**: o cartão foi cancelado em 2026-05 e a última fatura é a de abril, mas o Mobills exportou `202605`, `202606` e `202607` (os dois últimos vazios). O de 2026-05 tem 8 linhas, todas previsões de recorrência que ficaram presas ao cartão (no geral são `Pendente` de 09/05); as cobranças de verdade estão no VISA. Por isso o Youtube e o Google One de 2026-05 ficaram ambíguos (grupos 12 e 13). O PDF do banco que vence em 03/05/2026 traz as compras de abril e casa com o `2026-04` do Mobills.
- **Parcelas quebradas (342)**: a maior parte é defeito do reagrupamento, não dado faltando. Contando cada parcela que falta uma vez: 234 existem no mês certo com outro valor (117 compras partidas), 168 estão no geral sem o sufixo `(n/total)`, 12 sem sufixo e com outro valor, 27 com outra descrição, 28 em meses fora da sequência e 24 não estão no export. Só 11 sequências são "falta só no fim, com a última a partir de 2026-09". Uma amostra nos PDFs do Personnalite confirma que o banco cobrou as parcelas sem sufixo. A correção vai para o [ticket 219](219-importador-do-mobills-parcelas-com-outro-valor-ou-sem-sufixo.md).

### Decisões

- **Grupos ambíguos (Q1, Q7, Q9)**: "descarte os duplicados". Em cada grupo, a linha da fatura casa primeiro com a `Paga`; a `Pendente` que sobra é a duplicada e não entra (nem débito na conta, nem prevista). Vale também para o 2×2 "Mãe remedios" (Credicard 2021-04, duas linhas iguais na fatura): uma compra só. A aba passa a mostrar o descarte com a coluna `Decisão (descartar ou manter)`, em branco = descartar; `manter` devolve a linha (o par antigo, como hoje), para o caso de serem duas compras de verdade. A decisão fica entre as rodadas.
- **Situação (Q3)**: com a regra acima, a linha que fica é a `Paga`; nenhuma regra nova para o resto do cartão.
- **Cartão encerrado (Q8)**: a aba `Cartões` ganha a coluna `Última fatura` (`AAAA-MM`, no rótulo do Mobills); o importador ignora os arquivos de fatura depois dela. O Credicard fica com `2026-04`. As previsões que sobram no geral saem pela regra de pendente avulso.
- **Parcelas (Q4, Q5, Q12)**: parcela com outro valor no meio é a mesma compra, e a linha sem `(n/total)` no mês do buraco é a parcela que falta. A correção de `parcelas.py` é o ticket 219.
- **Parcelas quebradas (Q6, Q13)**: as 204 "ausentes" não são esperadas (são o defeito acima). Para o que sobrar, a aba ganha a coluna `Decisão (avulsas, parcelamento ou descartar duplicada)`: em branco ou `avulsas` como hoje; `parcelamento` vira um parcelamento só (as de antes contam como anteriores ao histórico, as que faltam depois da última são geradas como previstas); `descartar duplicada` tira a parcela repetida no mesmo mês. A decisão fica entre as rodadas pela chave que a aba já usa (descrição, valor, 1ª parcela, 1º mês).
- **PDFs (Q10, Q11, Q14)**: os PDFs são o documento-verdade do valor pago; a conferência do total de cada fatura pelo PDF é o [ticket 220](220-importador-do-mobills-conferir-faturas-pelo-pdf-do-banco.md).

### O que foi feito

- **Grupos ambíguos**: a fatura casa primeiro com a `Paga`; a `Pendente` que sobra fica de fora, com a linha de fatura que repete a data e o cartão de uma já casada. Uma linha de fatura de outra data continua casando com a pendente (são duas compras). A aba ganhou `Resultado` (`par`, `descartada`, `sem par`) e `Decisão (descartar ou manter)`. Nos exports reais: 11 linhas descartadas e 10 compras que deixam de entrar duas vezes (6.365 → 6.355 lançamentos).
- **Cartão encerrado**: no cartão **arquivado**, a `Última fatura` que o dono deixou na aba `Cartões` corta as faturas depois dela. No cartão ativo, a coluna só mostra o último arquivo, porque senão um export novo seria cortado pela rodada anterior. Com `2026-04` no Credicard, saem as 8 previsões de maio (→ 6.347).
- **Parcelas quebradas**: coluna `Decisão (avulsas, parcelamento ou descartar duplicada)`. A aba mostra as sequências como o export as traz, para a linha (e a decisão) não sumir quando o dono decide. Os dois pedaços aceitos de uma mesma compra não geram parcela em dobro.
- Decisão digitada fora das válidas vira impedimento e fica na planilha.

### Limites conhecidos (aceitos)

- A chave da sequência (descrição, valor, 1ª parcela, 1º mês) é a mesma para dois pedaços que começam na mesma parcela e no mesmo mês, como os de uma parcela duplicada; a decisão vale para os dois. Para `descartar duplicada` é o que se quer (fica uma).
- A chave do grupo ambíguo (mês, descrição, valor) não tem o cartão: dois grupos iguais em cartões diferentes no mesmo mês dividem a decisão.
- Dois pedaços aceitos como `parcelamento` continuam dois parcelamentos no app; juntá-los é do [ticket 219](219-importador-do-mobills-parcelas-com-outro-valor-ou-sem-sufixo.md), que deve fazer quase todos sumirem.

### Pendências gravadas

- [Ticket 217](217-importador-do-mobills-linha-de-fatura-duplicada-pelo-mobills.md): as linhas descartadas aqui não aparecem na Conferência nem na aba Faturas; se o Mobills as conta no total, a diferença fica sem explicação.
- [Ticket 219](219-importador-do-mobills-parcelas-com-outro-valor-ou-sem-sufixo.md): a parcela gerada para uma sequência aceita que acaba antes do último mês cai como prevista em mês já exportado; decidir com o dono se entra realizada.
