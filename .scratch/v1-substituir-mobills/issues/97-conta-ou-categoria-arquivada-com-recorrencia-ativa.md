# Conta ou categoria arquivada com recorrência ativa

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling`, `domain-modeling`; HITL (decisão do dono); depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: high
Issue: #178
Origem: [ticket 45](45-recorrencia-mudar.md): a tarefa diária segue gerando previstos numa conta ou categoria arquivada depois de criada a regra (a regra já as tinha, e `conferir_ligacoes` aceita o que a regra já tinha)

## O que decidir

O que acontece com a recorrência quando o casal arquiva a conta (ou o cartão) ou a categoria dela.

## Checklist

- [x] Decidir uma das saídas e registrar no `GLOSSARY.md` (ADR se for difícil de reverter):
  - arquivar encerra as recorrências da conta ou categoria (`ate` = hoje) e tira os previstos futuros;
  - arquivar avisa quantas recorrências ativas ela tem e deixa o casal escolher caso a caso;
  - nada muda (a recorrência segue gerando; hoje é este o comportamento)
- [x] Implementar a saída escolhida em `backend/app/lancamentos.py` (arquivar conta e categoria, `PATCH /api/categorias/{id}`, `PUT /api/contas/{id}`) e em `backend/app/recorrencias.py`, com testes de API
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

Recomendação do agente do ticket 45: avisar em vez de encerrar sozinho, para o arquivamento nunca apagar previstos sem o casal ver (história 108: nada some sozinho).

## Answer

Decidido com o dono (grilling): **avisar**, sem encerrar nada sozinho.

- Arquivar conta, cartão ou categoria não mexe nas recorrências: a **recorrência ativa** (com previsto de hoje em diante, não pulado nem confirmado) segue gerando previstos no item arquivado até o casal trocar o item daqui para frente ou encerrar a regra. Desarquivar também não mexe.
- Se alguma recorrência ativa usa o item, "Arquivar" abre antes um aviso com cada uma (descrição e próxima data, abrindo a tela dela pelo próximo previsto) e os botões **Arquivar mesmo assim** e **Cancelar**. Sem recorrência ativa, arquiva direto.
- No item arquivado, a linha em Contas e categorias (e na seção de cartões) lembra as recorrências ativas que seguem nele, até não sobrar nenhuma.
- A tela da recorrência mostra a conta, o cartão ou a categoria arquivada pelo nome, com "(arquivada)"/"(arquivado)".
- Tag e parcelamento ficam fora: a tag não muda para onde vai o dinheiro, e o parcelamento é compra já feita.
- O aviso vai pela regra (a conta e as categorias dela hoje), não por onde cada previsto está: o previsto alterado à mão para outra conta, ou os de antes de uma mudança daqui para frente que trocou a conta, não entram no aviso da conta antiga. A mudança não enviada da regra já vale no que o aparelho mostra, como no resto do app.

Implementação: `GET /api/recorrencias` (e as respostas de criar e mudar) trazem `proximo_previsto` (id e data) de cada regra; o app calcula o aviso e o lembrete com ele, sem repetir o calendário no aparelho (`web/src/contas-e-categorias/RecorrenciasAtivas.tsx`). Testes em `backend/tests/test_recorrencias.py` e `web/e2e/arquivar-com-recorrencia.spec.ts`. Glossário: **Recorrência ativa**, **Conta arquivada**, **Cartão arquivado**, **Categoria arquivada**. Sem ADR: nada se apaga, e voltar atrás é só tirar o aviso.

