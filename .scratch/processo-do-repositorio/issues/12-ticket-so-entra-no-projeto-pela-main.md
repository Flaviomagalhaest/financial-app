# Ticket só entra no projeto pela main

Type: task
Status: ready-for-human
Blocked by: —
Skills: `writing-for-agents` (AGENTS.md); HITL: o dono desliga o "Auto-add to project" do projeto
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #258
Origem: pedido do dono (31/10): as branches de feature criam tickets, a sincronização da branch os põe no projeto, e eles aparecem em TODO sem estar na `main`, porque o PR ainda não foi mesclado.

## Regra

A branch move o que já está no projeto (TODO para DOING, ou outra coluna); só a `main` põe issue no projeto. Assim, tudo o que aparece no projeto está na `main`.

## Checklist

- [x] `scripts/sincronizar-projeto.sh --so-no-projeto`: o ticket cuja issue não está no projeto fica de fora ("entra no merge para a main"), sem ler nem mudar a issue
- [x] `--tirar-sem-ticket` (só com a sincronização completa): tira do projeto as issues deste repositório que não são de nenhum ticket da `main`, as que entraram por uma branch antes desta regra
- [x] Workflow: a `main` roda com `--tirar-sem-ticket`, as branches com `--so-no-projeto`
- [x] AGENTS.md: a regra em "Como atualizar"; o passo "coloque a issue no projeto" sai de "Ticket novo"
- [x] Testado com um `gh` falso: na branch, o ticket fora do projeto não chama a API e o de dentro só muda a coluna; na `main`, só as issues sem ticket saem, e a de outro repositório fica; `--tirar-sem-ticket` com lista de tickets recusa
- [x] PR aberto para `main`
- [ ] (dono) No projeto, ⋯ → Workflows: desligar o "Auto-add to project". Depois, fechar este ticket

## Notas

Sem opção, o script continua pondo a issue no projeto, como na rodada à mão. A primeira rodada da `main` depois do merge tira do projeto as issues que entraram por branches ainda abertas; elas voltam no merge de cada uma.

O script não basta para a regra: a issue #258, deste ticket, apareceu no projeto em TODO logo ao ser criada, antes de qualquer sincronização (a primeira, run 41167782098, já a achou lá). Quem a pôs foi o próprio projeto, quase certamente o workflow nativo "Auto-add to project", que adiciona as issues novas do repositório e as deixa em TODO. Ele só se desliga na tela do projeto. Enquanto estiver ligado, a issue de um ticket novo aparece em TODO no momento em que a sessão a cria, e só sai na sincronização seguinte da `main`.
