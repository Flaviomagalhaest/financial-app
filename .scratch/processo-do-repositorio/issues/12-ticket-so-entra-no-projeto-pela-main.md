# Ticket só entra no projeto pela main

Type: task
Status: resolved
Blocked by: —
Skills: `writing-for-agents` (AGENTS.md); sem HITL além da revisão do PR
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

## Resolução

Sem opção, o script continua pondo a issue no projeto, como na rodada à mão. A primeira rodada da `main` depois do merge tira do projeto as issues que entraram por branches ainda abertas; elas voltam no merge de cada uma. Este ticket nasceu numa branch e é o primeiro a seguir a regra: a sincronização da branch o deixa de fora, e ele entra no projeto no merge.
