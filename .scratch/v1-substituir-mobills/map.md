# Mapa: V1 que substitui o Mobills

Label: wayfinder:map

## Destination

Spec da v1 do app de finanças do casal, pronta para `/to-spec` e `/to-tickets`, com as decisões de produto, modelo de dados e arquitetura na AWS tomadas e nenhum código de produção. A v1 substitui o Mobills: cobre os requisitos obrigatórios, a base de contas e cartões, a importação do histórico do Mobills desde 2019 e as funcionalidades complementares listadas em Notes.

## Notes

**Domínio:** finanças pessoais de um casal (Flávio e a esposa). Vocabulário em [GLOSSARY.md](../../GLOSSARY.md); decisões difíceis de reverter em `docs/adr/`.

**Skills por tipo de ticket:**

- `research`: skill `research` (AFK, em sub-agente). Os achados ficam numa branch `research/<nome>`, enviada e nunca mesclada, com um ponteiro no ticket.
- `grilling`: skills `grilling` e `domain-modeling` (HITL).
- `prototype`: skill `prototype` (HITL). O protótipo fica numa branch `prototipo/<nome>`, fora da `main`, com um ponteiro no ticket.
- `task`: o ticket traz o passo a passo; é HITL quando depende do dono.

**Requisitos obrigatórios da v1** (pedido original do dono):

1. Funciona na web, no Android e no iPhone.
2. Registro manual de gastos e receitas do dia a dia, com uma jornada fácil e rápida.
3. Compromissos futuros: parcelas no cartão, dívidas, seguros, salários.
4. Planejamento do mês por item (ex.: R$ 1.000 em alimentação, R$ 650 com carro, R$ 100 com farmácia).
5. Várias tags por lançamento ("trabalho", "saúde", "alimentação", "família").
6. Estatísticas com gráficos e dashboards.
7. Visão do cartão de crédito: uma linha no mês, com as compras e suas tags fáceis de consultar.
8. Roda na AWS com o menor custo possível, com o histórico de dados bem pensado (o casal usa o Mobills desde 2019).

**Base que vem do Mobills:** contas com saldo (corrente, poupança, carteira), transferências e pagamento de fatura como transferência.

**Funcionalidades complementares aceitas na v1:**

- Lançamento: funciona sem internet e sincroniza depois; favoritos e "repetir último"; atalho no ícone do Android que abre direto o novo lançamento (no iPhone não há atalho, ver [Plataforma do cliente](issues/08-plataforma-do-cliente.md)); sugestão automática de categorias e tags pelo histórico da descrição.
- Futuro: parcelamento com antecipação de parcelas e quitação do restante; recorrência com ou sem fim, mudando o valor daqui para frente ou só em um mês, sem mexer no resto; o previsto vira realizado quando acontece, com a lista do que venceu sem confirmação ("contas da semana").
- Planejamento: copiar do mês anterior ou de um modelo padrão; "quanto ainda posso gastar", contando o já gasto e o já previsto; aviso no momento de lançar (ex.: "Alimentação: 82% do planejado").
- Cartão: a compra cai na fatura certa pelos dias de fechamento e vencimento; limite comprometido pelas parcelas futuras; vários cartões e cartão adicional.
- Consulta: fechamento do mês; comparação com o mês anterior, com o mesmo mês do ano passado e ao longo dos anos; busca em todo o histórico com filtros salvos.
- Casal: pessoa e lançamento conjunto (ver o glossário); quem criou e quem alterou por último cada lançamento.
- Dados: projeção do saldo dos próximos meses; exportação de tudo (CSV ou backup).

**Preferências do dono:**

- Dois usuários, sem cadastro público e sem multi-inquilino, nem como objetivo futuro.
- Sem data fixa: a v1 está pronta quando der para largar o Mobills; a spec pode fatiar a v1 em etapas.
- Loja de apps não é requisito: basta ícone na tela inicial e boa experiência no celular.
- Backend em Python, para abrir caminho a cálculos de ciência de dados no futuro. O dono já usa Expo em outro repositório.
- Conta AWS nova, filha de uma conta de governança (AWS Organizations), no free tier com US$ 120 de crédito.
- Custo-alvo de US$ 0 a 1 por mês no uso normal, com teto de US$ 5 e alerta de orçamento na AWS.
- Sem domínio próprio: o endereço padrão da AWS basta para dois usuários.
- A primeira etapa da spec instala o app nos dois celulares (iPhone e Android) e testa o funcionamento sem internet, antes de construir em cima da PWA ([Plataforma do cliente](issues/08-plataforma-do-cliente.md)).
- Os dados reais do Mobills nunca entram no repositório; os tickets guardam só contagens e a forma dos dados.

## Decisions so far

- [Limites do app web instalável no iPhone e no Android](issues/02-limites-do-app-web-instalavel.md): PWA instalada no iPhone é isenta do apagamento de 7 dias, mas sem atalho de ícone nem Background Sync; Expo e Capacitor exigem Mac e, para ficar fora do perfil de 7 dias, Apple Developer (US$ 99/ano). Achados na branch `research/app-web-instalavel`.
- [Banco de dados na AWS para dois usuários e histórico longo](issues/03-banco-de-dados-na-aws.md): o volume é pequeno (13 a 61 MB) e DSQL e DynamoDB custam de 0 a ~US$ 1 por mês; Aurora Serverless v2 com pausa custa US$ 3 a 7 e RDS, US$ 14 a 29; o DSQL já tem foreign keys. Achados na branch `research/banco-de-dados-aws`.
- [Reconferir as lacunas das pesquisas de plataforma e de banco](issues/15-reconferir-lacunas-das-pesquisas.md): nada derruba uma opção sozinho; dados só no aparelho são arriscados em PWA e Capacitor (servidor como fonte de verdade); Expo e Capacitor no iPhone sem conta paga pedem reinstalação a cada 7 dias e Mac; DSQL não tem PITR; retomada do banco e sideload no Brasil ficam para o [ticket 17](issues/17-medir-retomada-e-confirmar-pontos-no-prototipo.md). Achados na branch `research/lacunas-plataforma-e-banco`.
- [Plataforma do cliente](issues/08-plataforma-do-cliente.md): o app é uma PWA em React + TypeScript, uma base de código para web, Android e iPhone, sem loja, sem Apple Developer e sem Mac. No iPhone, sem atalho no ícone e com a fila offline enviada só com o app aberto; no Android, atalho "Novo lançamento" no toque longo. Capacitor é o plano B; a primeira etapa da spec valida a instalação e o offline nos dois celulares. [ADR 0005](../../docs/adr/0005-app-web-instalavel-em-vez-de-app-nativo.md).
- [Em que mês conta uma compra no cartão](issues/06-em-que-mes-conta-uma-compra-no-cartao.md): compra no cartão conta no mês da fatura (o mês do fechamento), no planejamento, nas tags, no resumo e na projeção mês a mês; só o saldo da conta segue o pagamento real. Uma fatura por mês por cartão; estorno conta na fatura em que aparece. [ADR 0003](../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md).
- [Ciclo de vida do lançamento futuro](issues/05-ciclo-de-vida-do-lancamento-futuro.md): o compromisso futuro é um lançamento **previsto** que vira **realizado**; recorrência e parcelamento são regras que geram lançamentos (a compra parcelada não é lançamento). Confirmação manual por padrão; recorrência de valor fixo e parcelamento podem ser automáticos. Mudanças valem daqui para frente ou só num mês, sem mexer em realizados; receitas seguem as mesmas regras. [ADR 0004](../../docs/adr/0004-previsto-e-situacao-do-lancamento.md).
- [Categoria única ou só tags](issues/04-categoria-unica-ou-so-tags.md): o lançamento tem uma ou mais **categorias** (listas planas para despesa, receita e transferência), a **tag** é um rótulo pontual ("novo ap") e a **pessoa** é um campo próprio. Por categoria e por tag, o lançamento conta o valor inteiro em cada uma, sem pizza; no planejamento, conta em no máximo um item, escolhido pelo casal quando há mais de um. As categorias e tags do Mobills entram por um de-para revisado pelo dono. [ADR 0006](../../docs/adr/0006-varias-categorias-e-um-item-do-planejamento.md).
- [Dashboards e fechamento do mês](issues/11-dashboards-e-fechamento-do-mes.md): a v1 é um app com abas (Hoje, Mês, Cartões, Histórico, Futuro), com "ainda dá para gastar" em destaque, o fechamento do mês em texto corrido, a comparação por categoria contra o mês anterior e o mesmo mês do ano passado, e o cartão numa linha que abre as compras. Sem pizza: barras e listas bastam. A projeção de saldo mostra duas linhas, só com os previstos e com o que falta do planejamento. Protótipo na branch `prototipo/dashboards`.

## Not yet specified

- **Sincronização offline e conflitos:** como um lançamento feito sem internet chega ao servidor e o que acontece quando os dois editam o mesmo lançamento. Depende da plataforma e do banco.
- **Importação do Mobills** (em aberto no [ticket 18](issues/18-importacao-do-mobills-cartao-e-datas.md); formato e limitações em [O que o Mobills exporta](issues/01-o-que-o-mobills-exporta.md)): como as contas, cartões, faturas e parcelas de lá viram os conceitos daqui (categorias e tags entram por um de-para, ver [Categoria única ou só tags](issues/04-categoria-unica-ou-so-tags.md)), e como é o dia da virada (onde se lança durante a transição). O pendente/efetivado do Mobills vira previsto/realizado, e as parcelas de lá precisam ser reagrupadas em parcelamentos.
- **Sugestão automática de categorias e tags:** de onde vem a sugestão e como ela aprende com o uso.
- **Limite comprometido do cartão:** como mostrar quanto do limite as parcelas futuras ocupam.
- **Busca e filtros salvos:** o que se busca e o que um filtro salvo guarda.
- **Exportação:** formato e conteúdo do CSV e do backup.

## Out of scope

- Importar extrato ou fatura (OFX/CSV) e Open Finance: na v1 o lançamento é manual.
- Conferência da fatura em lote a partir do arquivo da fatura: o dono já prevê essa funcionalidade para depois da v1.
- Leitura do QR code da nota fiscal (NFC-e), foto de recibo e anexo de comprovante: automação de entrada fica para depois da v1.
- Lançamento por voz ou texto livre com IA: idem.
- Metas e caixinhas; patrimônio e investimentos: não servem para largar o Mobills.
- Comparações corrigidas pela inflação (IPCA): idem.
- Notificações (fatura fechando, planejamento estourando): idem.
- Divisão de despesas do casal ("quem deve a quem"): a pessoa já diz de quem é cada lançamento.
- Dividir um lançamento em partes com tags diferentes: o dono não quer se preocupar com isso agora.
- Dívida com juros calculada pelo app (tabela Price ou SAC): dívidas entram como parcelamento ou recorrência, com os valores já conhecidos.
- Sobra do planejamento que passa para o mês seguinte (envelope acumulado): fica para depois da v1.
- Histórico completo de alterações de um lançamento: na v1 basta saber quem criou e quem alterou por último.
- Recorrência por dia útil ("5º dia útil", "fim de semana vai para segunda") e calendário de feriados: na v1 a recorrência tem dia fixo e a data real se ajusta na confirmação.
- Estimativa que aprende (o previsto da conta de luz usar o último valor confirmado): na v1 o previsto usa o valor da regra.
