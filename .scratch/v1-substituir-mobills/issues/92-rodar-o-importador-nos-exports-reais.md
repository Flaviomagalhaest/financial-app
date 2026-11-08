# Rodar o importador do Mobills nos exports reais e conferir

Type: task
Status: ready-for-human
Blocked by: —
Skills: `run` (o dono roda localmente; HITL: só ele tem os exports reais)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #174
Origem: [ticket 67](67-importador-do-mobills-cruzamento-e-revisao.md) (o importador só rodou sobre exports fictícios; dado real nunca entra no repositório nem no CI)

## O que fazer

O dono roda o importador sobre `data/historic/` (fora do git) e cola aqui **só contagens**, sem nenhum dado real:

```sh
(cd backend && uv run python -m app.mobills <pasta do geral> <pasta das faturas> <planilha.xlsx>)
```

## Checklist

- [x] Layout: o geral numa pasta, uma subpasta por cartão com os arquivos `<cartão>_-_<AAAAMM>.xlsx`; se os exports estiverem em outro arranjo, ajustar `backend/app/mobills/leitura.py`
- [x] Taxa de casamento perto dos 97,7% do [ticket 18](18-importacao-do-mobills-cartao-e-datas.md) (4.618 exatos, 11 só sem a categoria, 2 prováveis, 111 sem par); se ficar longe, diagnosticar a comparação da descrição (hoje sem diferença de maiúsculas e de espaços)
- [ ] Separador de várias tags: conferir no export real se é a vírgula (`_tags` em `leitura.py` é uma aposta; os exports de teste só tinham uma tag por linha)
- [x] A Conferência termina no último mês com lançamento pago: confirmar que é o mês do export (a virada) e que os meses seguintes, só de previstos, podem ficar de fora. O mesmo mês decide os pendentes avulsos descartados (ticket 68): se o export sair num dia em que o mês corrente ainda não tem nada pago, os pendentes desse mês entram como previstos
- [ ] Parcelas (ticket 68): contar as sequências quebradas, que entram como lançamentos avulsos, sem parcelamento e sem gerar as que faltam (o limite não conta as previstas delas como parcelas futuras); as parcelas de um parcelamento de cartão sem fatura em mês já exportado, que ficam na conta enquanto o parcelamento fica no cartão; e se o centavo da divisão aparece (a parcela gerada copia o valor da última que veio)
- [x] Ajustes sem cartão (ticket 68): se aparecem e se há dois reajustes iguais no mesmo mês, que dividem a escolha do cartão
- [ ] Dono preenche a coluna Mobills da Conferência (feito, 13 meses) e das Faturas (falta) em alguns meses, roda de novo e confere a diferença e o "Por quê"
- [ ] Dono diz se as abas Grupos ambíguos e Parcelas quebradas bastam como informação ou se precisam de uma coluna de decisão (hoje só informam: o ticket 18 manda o grupo e a sequência "para a revisão" sem dizer o que o dono decide); se precisar, vira ticket
- [x] Contagens e respostas gravadas em `## Answer`

## Answer

Rodado em 2026-11-08 pelo agente, na máquina do dono, sobre `data/historic/` (fora do git; a planilha de revisão ficou em `data/saida92/`, também fora). Só contagens. O comando saiu com código 2 (a planilha ainda tem impedimentos de edição: 2 da aba Cartões), como esperado numa primeira rodada.

- **Layout**: bate com o esperado, sem ajuste em `leitura.py`. O geral são 3 arquivos em `Transações/` e as faturas são 219 arquivos em 7 subpastas de `Cartões/`. 6.365 lançamentos, 4.863 no cartão.
- **Casamento**: 4.628 de 4.742 linhas de fatura casadas (**97,6%**; o ticket 18 media 97,7%). 0 pares prováveis, 13 grupos ambíguos (13 pagos e 13 pendentes no geral), 10 linhas de "Categoria diferente". Não precisa diagnosticar a comparação da descrição.
- **Separador de tags**: **não dá para confirmar**. Das 12.590 linhas lidas do geral, 618 têm tag e nenhuma traz `,` `;` `|` ou `/`: o export real também só tem uma tag por linha. A vírgula segue como aposta, e o comentário de `_tags` fica como está.
- **Conferência**: 93 meses, de 2019-02 a **2026-10**. Termina em 2026-10, o último mês com lançamento pago; o export provavelmente saiu na virada de outubro para novembro. O dono confere se foi essa a data do export.
- **Parcelas quebradas**: 342 sequências (216 com cartão, 126 sem). 337 têm parcela faltando (101 só no começo, 79 só no fim, 157 nos dois lados) e 16 têm parcela duplicada no mesmo mês (5 só com duplicada). As 79 com falta só no fim têm a última parcela a partir de 2026-09, ou seja, são as que ainda não chegaram e podem ser compras do mês corrente ainda em andamento. Os 342 são muito mais que nos exports de teste; o dono diz se é esperado.
- **Parcelamentos sem cartão** (aba própria): 135 parcelamentos aguardando a escolha do cartão.
- **Ajustes sem cartão**: **0**; logo não há dois reajustes iguais no mesmo mês. Os 10 ajustes de fatura que o importador conta têm cartão.
- **Centavo da divisão**: não verificado (exige comparar a parcela gerada com a do Mobills, que só o dono tem).

### Conferência contra o Mobills (dono preencheu 13 meses da Conferência)

- 11 dos 13 meses fecham com diferença 0.
- **2022-11, diferença -50,00**: um dos dois lançamentos de 50,00 do mês é uma "transação ignorada" no Mobills, que o export não distingue (vem como `Paga`). Decisão do dono: fica fora da conta. Vira o [ticket 215](215-importador-do-mobills-deixar-de-fora-os-lancamentos-ignorados.md).
- **2023-11, diferença -196,30** (nosso 154,35, Mobills 350,65): as duas compras do cartão sem par (149,62 e 46,68, que somam exatamente 196,30) existem na fatura do app do Mobills, mas o geral não as traz. É o caso das 111 linhas de fatura sem par do ticket 18: o importador as inclui por regra, e o "Por quê" da Conferência as lista. Diferença esperada, não é erro. Sobram 3,64 (quatro estornos sem par da mesma fatura) cuja contagem não bate com o "Por quê" (-192,66); fica como pendência pequena, sem ticket.

### Falta o dono

- Preencher a coluna Mobills da aba Faturas em alguns meses (a da Conferência já foi) e conferir a diferença e o "Por quê".
- Dizer se as abas Grupos ambíguos (26 linhas) e Parcelas quebradas (342) bastam como informação ou precisam de uma coluna de decisão; com 342, é provável que precisem.
- Dizer se os 342 de parcelas quebradas são esperados (compras avulsas lançadas como parcelas em meses fora dos exports) ou sinal de problema em `parcelas.py`.
