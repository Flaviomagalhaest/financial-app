# Conferir o crédito de US$ 120 e o compartilhamento de créditos na conta AWS

Type: task
Status: resolved
Blocked by: —
Skills: nenhuma de tipo; tarefa HITL (o dono confere no console da conta pagadora e na conta nova); apoio: `research` para consolidar o que o dono trouxer
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #34
Origem: item "Conta AWS (HITL)" de [Reconferir as lacunas das pesquisas de plataforma e de banco](15-reconferir-lacunas-das-pesquisas.md); lacuna de [Banco de dados na AWS para dois usuários e histórico longo](03-banco-de-dados-na-aws.md) (a FAQ da AWS se contradiz sobre a validade dos créditos)

## Question

Qual o prazo e a origem dos US$ 120 de crédito da conta nova, e o compartilhamento de créditos está ligado na conta pagadora (o gasto de outras contas da organização consome esse crédito)?

## Checklist

- [x] No console da conta nova (Billing > Credits): saldo e prazo conferidos; origem de cada crédito não detalhada (ver Answer)
- [x] Compartilhamento de créditos: o dono decidiu **não desligar**
- [x] Anotar se as franquias "sempre grátis" de DSQL e DynamoDB (por conta pagadora) estão sendo usadas por outras contas da organização
- [x] Resultado em `## Answer`; dizer se muda o custo estimado de [Banco de dados e região](09-banco-de-dados-e-regiao.md)

## Answer

Conferido pelo dono no console (visão geral do Billing, 2026-10-25):

- **Saldo:** US$ 119,98 de crédito restante (consumo quase zero até agora).
- **Prazo:** o painel mostra o plano grátis com **171 dias restantes, até 12/04/2027**, ou seja, 6 meses a partir da criação da conta. Trate o crédito como válido até essa data (a leitura "6 meses" da FAQ, que a pesquisa já adotava). O que sobrar nessa data deixa de valer.
- **Origem do crédito:** o painel não detalhou cadastro versus atividades; o saldo é US$ 119,98 e isso basta para o planejamento. Não vale mais investigar.
- **Projetos:** a conta tem 2 projetos e 1 membro de equipe. O outro projeto está começando, com custo muito baixo, e **usa DynamoDB**.
- **Compartilhamento de créditos:** o dono decidiu **mantê-lo ligado**. O gasto do outro projeto consome o mesmo crédito, o que é aceitável pelo custo baixo.
- **Franquias "sempre grátis":** DynamoDB é usado pelo outro projeto e a franquia é por região e por conta pagadora, então ela é **compartilhada**. DSQL não é usado por outros. Se o app escolher DynamoDB, ele divide a franquia (25 GB, 25 WCU/RCU provisionadas) com o outro projeto; o volume de armazenamento de ambos é pequeno, então o risco é baixo, mas deve ser considerado.
- **Cobrança futura:** o dono pode adicionar um cartão e passar para o plano pago sem problema. Portanto o estouro do crédito ou o fim do prazo não é bloqueio, só vira cobrança normal.

**Muda o custo estimado de [Banco de dados e região](09-banco-de-dados-e-regiao.md)?** Não de forma relevante. O custo estimado de DSQL ou DynamoDB (de US$ 0 a cerca de US$ 1 por mês) fica coberto pelos US$ 119,98 durante todo o prazo, mesmo somando o outro projeto. Dois efeitos para o ticket 09: (1) o crédito vence em 12/04/2027, então a decisão deve assumir cobrança normal depois disso (já dentro do teto de US$ 5); (2) se a escolha for DynamoDB, a franquia é dividida com o outro projeto.

## Comments
