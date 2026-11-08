# Importador do Mobills: deixar de fora os lançamentos ignorados

Type: task
Status: resolved
Blocked by: —
Skills: `grilling` (HITL: o dono decide como marcar o que fica de fora, já que o export não traz a marca); depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #565
Origem: [ticket 92](92-rodar-o-importador-nos-exports-reais.md) (na Conferência de 2022-11 a diferença de -50,00 era um lançamento que o Mobills marca como "transação ignorada")

## O que construir

No Mobills, a "transação ignorada" fica fora das contas do app, mas o export não a distingue: a linha vem com `Situação: Paga` como qualquer outra (o geral real só traz `Paga` e `Pendente`), e o importador a conta. O dono decidiu que o que o Mobills ignora **fica fora da conta** no app.

Como o export não diz quais são, é preciso um jeito de o dono marcar. A decidir na sessão (`grilling`): uma aba da planilha de revisão (por exemplo "Ignorados", com `Arquivo do geral` e `Linha no arquivo`, como a aba Grupos ambíguos já faz) ou outra forma; como o dono acha as ignoradas no app do Mobills; e se a marca sobrevive às rodadas seguintes.

## Checklist

- [x] Decisão do mecanismo (grilling); sem registro na planilha de revisão, por decisão do dono (veja `## Answer`)
- [x] A linha marcada não entra em lançamentos, Conferência, Faturas nem cruzamento
- [x] Teste: a linha marcada some e a Conferência do mês fecha (caso do ticket 92: 2022-11, "Passagem Ester", 50,00)
- [x] Dono lista as ignoradas dos outros meses (são só duas, em todos os anos)

## Answer

Grilling com o dono em 2026-11-08, depois de ler o [ticket 216](216-importador-do-mobills-decisao-para-grupos-ambiguos-e-parcelas-quebradas.md) (decisão por chave de conteúdo, filtro antes do cruzamento como o do cartão arquivado).

### Fatos

O dono listou as únicas transações ignoradas no Mobills em todos os anos, as duas na Carteira:

- 08/07/2024, "Sem parar", categoria "Mãe estorno", R$ 230,47;
- 28/11/2022, "Passagem Ester " (com espaço no fim), categoria "Ester", R$ 50,00. Em 2022-11 há dois lançamentos de 50,00; só um é o ignorado.

### Decisões

- **Sem aba na planilha**: com só duas, conhecidas e que não mudam mais (o Mobills vai ser substituído), a lista fica numa constante `IGNORADAS` em `backend/app/mobills/importacao.py`. A planilha de revisão não muda.
- **Chave**: data, descrição sem espaços nas pontas, conta e valor sem o sinal (como a tela do Mobills mostra); a categoria fica de fora. Cada item tira uma linha só: das duas de 50,00 em 2022-11, uma fica.
- **Onde sai**: a linha sai do geral antes do cruzamento, como as faturas depois da `Última fatura` do cartão arquivado (216). Fica fora de lançamentos, Conferência, Faturas, parcelas e cruzamento, e a Conferência do mês fecha com o Mobills, que também não a conta; não aparece no "Por quê" (sem diferença a explicar, ao contrário do [ticket 217](217-importador-do-mobills-linha-de-fatura-duplicada-pelo-mobills.md)).
- **Não achada**: vira aviso na saída da linha de comando (`aviso: ignorada não achada no geral: ...`), sem impedir gravar, porque os testes e um export parcial não as trazem.
- **Cartão e parcela**: fora do escopo, porque nenhuma das duas é compra de cartão nem parcela.

### O que foi feito

- `IGNORADAS` e `_sem_as_ignoradas` em `importacao.py`; `Importacao.avisos`, que `python -m app.mobills` mostra.
- Testes em `test_importador_mobills.py`: os dois casos reais saem, a outra "Passagem Ester" e um "Sem parar" de outro valor ficam, e a Conferência de 2022-11 fecha com o valor do Mobills; a ignorada que o export não traz só vira aviso. `test_backup_do_importador.py` confere o aviso na saída.
- Termo **Transação ignorada no Mobills** no `GLOSSARY.md`; parágrafo no README (Importador do Mobills).

### Pendências

Nenhuma nova.
