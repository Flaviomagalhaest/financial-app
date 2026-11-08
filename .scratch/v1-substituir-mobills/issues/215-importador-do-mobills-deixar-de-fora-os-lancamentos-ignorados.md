# Importador do Mobills: deixar de fora os lançamentos ignorados

Type: task
Status: ready-for-human
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

- [ ] Decisão do mecanismo (grilling) e registro na planilha de revisão
- [ ] A linha marcada não entra em lançamentos, Conferência, Faturas nem cruzamento
- [ ] Teste: a linha marcada some e a Conferência do mês fecha (caso do ticket 92: 2022-11, "Passagem Ester", 50,00)
- [ ] Dono lista as ignoradas dos outros meses (a Conferência só foi comparada em 13 meses)
