# Busca e filtros salvos

Type: grilling
Status: claimed
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono); apoio: `prototype` se a resposta pedir ver a tela
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #72
Origem: fog "Busca e filtros salvos" do [mapa V1 que substitui o Mobills](../map.md), graduado agora que as abas ([ticket 11](11-dashboards-e-fechamento-do-mes.md)) e a importação do histórico ([ticket 18](18-importacao-do-mobills-cartao-e-datas.md)) estão decididas

## Question

O que o casal busca em todo o histórico, o que um filtro salvo guarda e como funciona a edição em lote (selecionar vários lançamentos e trocar ou acrescentar categorias e tags de uma vez)?

Pontos a decidir:

- por quais campos se busca (descrição, valor, categorias, tags, conta, cartão, pessoa, período, situação) e se a busca é de texto livre, de filtros combinados ou das duas coisas;
- o que um filtro salvo guarda (os critérios, o período fixo ou relativo, a ordenação) e quem o vê (o casal inteiro ou cada pessoa);
- como a busca conta o lançamento no cartão (mês da fatura, [ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md)) e o que mostra além da lista (total e quantidade do resultado);
- a edição em lote: o que muda de uma vez, como o casal confere antes de aplicar e se dá para desfazer; precisa acertar o histórico importado do Mobills;
- o comportamento sem internet ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)): a busca roda no aparelho, no servidor ou nos dois, e como um lote entra na fila.

## Checklist

- [ ] Decisão registrada em `## Answer`
- [ ] Vocabulário novo no `GLOSSARY.md` e ADR para o que for difícil de reverter
- [ ] Linha em "Decisions so far" do mapa e item removido de "Not yet specified"
