# Busca e filtros salvos

Type: grilling
Status: resolved
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

- [x] Decisão registrada em `## Answer`
- [x] Vocabulário novo no `GLOSSARY.md` e ADR para o que for difícil de reverter
- [x] Linha em "Decisions so far" do mapa e item removido de "Not yet specified"

## Answer

Decidido com o dono em 2026-10-27. A busca é uma **tela única de resultado**, com filtros combinados e texto livre, **filtros salvos** do casal e **edição em lote** de categorias e tags.

**Busca**
- Texto livre (descrição) mais filtros em chips, numa tela só, na aba Histórico, com lupa em qualquer aba. Os atalhos "ver os lançamentos" do ranking do Mês e da aba Cartões abrem essa tela já filtrada.
- Filtros: descrição, valor (mínimo e máximo), categorias, tags (qualquer das escolhidas; também "sem categoria" e "sem tag"), conta, cartão, **fatura** (cartão e mês da fatura), pessoa (inclui Conjunto), período, situação (previsto ou realizado) e tipo (despesa, receita, transferência). Entre filtros é E, dentro de um filtro é OU.
- **Período usa a data da compra** na compra no cartão ("março" traz o que foi comprado em março, qualquer que seja a fatura) e a data do lançamento no resto. É uma exceção consciente ao [ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md), que vale para planejamento, tags, resumo e projeção ([ADR 0013](../../../docs/adr/0013-busca-por-data-da-compra-e-fatura-a-parte.md)). Quem quer o mês da fatura usa o filtro **Fatura**.
- Cada linha mostra a data da compra e, no cartão, o mês da fatura. Ajuste de fatura não aparece (não é lançamento, [ADR 0008](../../../docs/adr/0008-ajuste-de-fatura-fica-na-fatura.md)); o pagamento de fatura só aparece com o tipo transferência.
- **Compra parcelada**: o resultado traz uma linha por compra, com a data da compra, o valor **total** e as parcelas (`03/04 - R$ 2.500,00 (10x)`); tocar abre as parcelas, cada uma com o mês da fatura e a situação. Com o filtro **Fatura**, cada parcela é uma linha própria, com o valor e `03/10`.
- No topo: quantidade, total de despesas, total de receitas e saldo; transferência fora dos totais; previstos somados à parte. A compra parcelada conta pelo valor total, uma vez; com o filtro Fatura, pelo valor da parcela. O filtro de valor segue a mesma regra. Uma linha fixa avisa "período por data da compra; a aba Mês conta pelo mês da fatura" e some com o filtro Fatura, onde os números batem com o Mês.
- Ordem: mais recente primeiro (padrão) ou por valor; lista paginada, sem teto.
- **Sem internet**: a busca completa exige internet e roda no servidor. Sem ela, vale só o que o aparelho já guarda (recentes e não enviados do próprio aparelho), com aviso "resultado parcial, sem internet".

**Filtro salvo**
- Guarda nome, critérios (texto e filtros) e ordenação; o período é relativo ("este mês", "últimos 90 dias") ou fixo, à escolha de quem salva. Não guarda seleção de lançamentos.
- É do casal inteiro, sem filtro privado. Criar, editar e apagar exigem internet; sem rede aparece em leitura.

**Edição em lote**
- Atua sobre os marcados no resultado (com "selecionar todos do resultado" e "limpar seleção") e muda só **categorias e tags**: acrescentar, remover, trocar uma por outra ou substituir tudo. Pessoa, conta, valor, data e situação ficam fora na v1.
- Prévia antes de aplicar: quantos mudam, amostra dos 5 primeiros (antes e depois) e quantos já estão como pedido. Selecionar uma compra parcelada seleciona o parcelamento todo; a contagem diz "12 compras (58 lançamentos)".
- Aplica tudo ou nada. Desfazível por 30 dias; o desfazer pula os lançamentos que outra pessoa mudou depois e avisa quais.
- A prévia avisa quantos lançamentos trocam de item do planejamento ([ADR 0006](../../../docs/adr/0006-varias-categorias-e-um-item-do-planejamento.md)) sem bloquear; um lote que deixaria despesa ou receita sem categoria é recusado.
- Exige internet: não entra na fila e não gera conflito ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)); o servidor aplica ou recusa o lote inteiro.

**Registrado**: ADR 0013; termos **Filtro salvo** e **Edição em lote** no `GLOSSARY.md`.

Fica para a spec: o formato exato da prévia, o índice de busca no servidor e o prazo de 30 dias do desfazer, que é valor inicial.
