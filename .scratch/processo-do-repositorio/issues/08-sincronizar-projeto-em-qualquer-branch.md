# Sincronizar o projeto a cada push em qualquer branch

Status: resolved
Blocked by: —
Skills: `writing-for-agents` (para o AGENTS.md); sem HITL além da revisão do PR
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #51
Origem: pedido do dono na sessão do [ticket 18 da V1](../../v1-substituir-mobills/issues/18-importacao-do-mobills-cartao-e-datas.md): a reserva do ticket só virava DOING no kanban depois do merge do PR

## Problema

O workflow `sincronizar-projeto.yml` rodava só em push na `main`. A coluna do projeto ficava parada enquanto o ticket mudava numa branch de trabalho ou de reserva, e só andava no merge.

## Checklist

- [x] Workflow roda em push de qualquer branch que mude um ticket ou o script
- [x] Na `main`, sincroniza todos os tickets, como antes
- [x] Nas outras branches, sincroniza só os tickets que a branch adicionou ou mudou: desde o push anterior (`github.event.before`) ou, no primeiro push e no `workflow_dispatch`, desde o ponto em que a branch saiu da `main`
- [x] Push que apaga branch não roda
- [x] `AGENTS.md` (reserva e "Como atualizar") descreve o novo gatilho
- [ ] Conferir no primeiro push de uma branch depois do merge que a coluna anda (ex.: a próxima reserva vai para DOING sem esperar o merge)

## Answer

O workflow passou a rodar em push de qualquer branch. Nas branches que não são a `main`, ele passa ao `scripts/sincronizar-projeto.sh` só os tickets mudados, para uma branch antiga não reverter a coluna de tickets que ela não tocou. A `main` continua espelhando tudo, então um desvio deixado por uma branch abandonada se acerta no merge seguinte que mude um ticket.

Consequência a conhecer: um ticket marcado `resolved` numa branch fecha a issue e vai para FINISHED já no push, antes do merge; se o PR for recusado, a issue só reabre no próximo push da `main` que mude um ticket (ou rodando o workflow à mão).
