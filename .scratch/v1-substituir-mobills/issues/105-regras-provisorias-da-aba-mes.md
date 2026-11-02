# Conferir as regras provisórias da aba Mês

Type: grilling
Status: resolved
Blocked by: 54
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se uma regra mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #208
Origem: [ticket 54](54-aba-mes.md): a spec, o [ticket 11](11-dashboards-e-fechamento-do-mes.md) e o protótipo não dizem o que fazer nestes casos, e o 54 escolheu um comportamento provisório para cada um (em `backend/app/meses.py`, com teste em `backend/tests/test_aba_mes.py`, e no texto de `web/src/mes/apresentacao.ts`)

## As perguntas

1. **O que é "guardado" no fechamento.** Hoje: a soma das transferências **realizadas com categoria** no mês (o exemplo do glossário, "guardar na reserva"). Um resgate da reserva com categoria também soma, e nada desconta. Alternativas: só as que vão para conta poupança, o líquido (entra menos sai da poupança) ou só as categorias que o casal marcar.
2. **O fechamento conta só o realizado**, como o protótipo (`fechou com ${t.rec.r} de receitas e ${t.desp.r} de despesas`): o previsto que ficou sem confirmar num mês passado sai das receitas, das despesas, da sobra e da variação, e o texto diz quantos ficaram. Já os itens que "passaram do planejado" seguem a regra do planejamento (realizado mais previsto, história 119), e a comparação e o ranking somam realizado e previsto. O dono confirma se o fechamento deve ser assim.
3. **A variação do fechamento é só das despesas** (como o protótipo). A história 124 fala em "a variação contra o mês anterior e o mesmo mês do ano passado" sem dizer de quê: comparar também as receitas e a sobra?
4. **"Livre" e "ainda dá para gastar" na mesma tela.** A barra do mês atual mostra o livre como o planejado dos itens de despesa menos todas as despesas do mês (como o protótipo: `livre=Math.max(0,plan-t.desp.r-t.desp.p)`), o que compensa um item estourado com a sobra de outro e conta despesa sem item. Logo abaixo, "Ainda dá para gastar" é a soma do que falta em cada item, sem compensar (história 118). Os dois números podem divergir: manter, unificar ou explicar na tela?
5. **Meses futuros.** As setas vão também para os meses seguintes (para copiar o planejamento ou aplicar o modelo padrão antes de o mês começar), com a barra do mês e sem fechamento. A história 122 fala só de "qualquer mês do histórico".
6. **Avisos que não estavam no protótipo**: "Passou R$ X do planejado" embaixo da barra e o parágrafo dos previstos sem confirmar no fechamento. Ficam?

## Checklist

- [x] O dono responde cada pergunta e a resposta vai para `## Answer`
- [x] Se uma regra mudar: teste de API em `backend/tests/test_aba_mes.py`, ajuste em `backend/app/meses.py` e, no texto, em `web/src/mes/apresentacao.ts`; o README (seção Planejamento) acompanha

## Answer

1. **Guardado**: mantém. Transferências realizadas com categoria, soma simples.
2. **Fechamento só do realizado**: mantém, com o aviso dos previstos sem confirmar.
3. **Variação**: muda. O fechamento compara **despesas, receitas e sobra** contra o mês anterior e o mesmo mês do ano passado. A base da variação da sobra é o módulo da sobra antiga; sem base (zero), não há porcentagem. Campos novos `variacao_receitas_*` e `variacao_sobra_*` em `Fechamento`; texto com um parágrafo de comparação por assunto.
4. **Livre x ainda dá para gastar**: mantém os dois como estão, sem explicação na tela.
5. **Meses futuros**: mantém as setas para o futuro.
6. **Avisos extras**: ficam os dois.

Mudanças: `backend/app/meses.py`, `backend/tests/test_aba_mes.py`, `web/src/mes/apresentacao.ts`, `openapi.json`, `web/src/api/schema.d.ts` e README (seção Planejamento).
