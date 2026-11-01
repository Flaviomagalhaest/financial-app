# Conta ou categoria arquivada com recorrência ativa

Type: grilling
Status: claimed
Blocked by: —
Skills: `grilling`, `domain-modeling`; HITL (decisão do dono); depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: high
Issue: #178
Origem: [ticket 45](45-recorrencia-mudar.md): a tarefa diária segue gerando previstos numa conta ou categoria arquivada depois de criada a regra (a regra já as tinha, e `conferir_ligacoes` aceita o que a regra já tinha)

## O que decidir

O que acontece com a recorrência quando o casal arquiva a conta (ou o cartão) ou a categoria dela.

## Checklist

- [ ] Decidir uma das saídas e registrar no `GLOSSARY.md` (ADR se for difícil de reverter):
  - arquivar encerra as recorrências da conta ou categoria (`ate` = hoje) e tira os previstos futuros;
  - arquivar avisa quantas recorrências ativas ela tem e deixa o casal escolher caso a caso;
  - nada muda (a recorrência segue gerando; hoje é este o comportamento)
- [ ] Implementar a saída escolhida em `backend/app/lancamentos.py` (arquivar conta e categoria, `PATCH /api/categorias/{id}`, `PUT /api/contas/{id}`) e em `backend/app/recorrencias.py`, com testes de API
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

Recomendação do agente do ticket 45: avisar em vez de encerrar sozinho, para o arquivamento nunca apagar previstos sem o casal ver (história 108: nada some sozinho).
