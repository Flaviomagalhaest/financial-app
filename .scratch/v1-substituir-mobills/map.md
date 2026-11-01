# Mapa: V1 que substitui o Mobills

Label: wayfinder:map

## Destination

Spec da v1 do app de finanças do casal, pronta para `/to-spec` e `/to-tickets`, com as decisões de produto, modelo de dados e arquitetura na AWS tomadas e nenhum código de produção. A v1 substitui o Mobills: cobre os requisitos obrigatórios, a base de contas e cartões, a importação do histórico do Mobills desde 2019 e as funcionalidades complementares listadas em Notes.

Spec escrita: [spec.md](spec.md).

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
- [Fluxo de lançamento rápido](issues/10-fluxo-de-lancamento-rapido.md): valor primeiro, num teclado na tela; conta e categorias em fileiras de toque logo abaixo; descrição com sugestão pelo histórico, tags, pessoa, data, parcelado e recorrente numa folha de detalhes opcional; "repetir último" com o lançamento vazio; aviso de planejamento com o antes e o depois e a escolha do item trocável com um toque; contas da semana num aviso da tela inicial, com confirmar em um toque. Favoritos ([ticket 19](issues/19-onde-ficam-os-favoritos.md)): fileira acima do teclado e grade na tela inicial, com a mesma lista; o favorito preenche tudo com o último valor como padrão, editável, e "Salvar" confirma; viram favorito à mão (⭐) ou por sugestão dos mais usados. Protótipos nas branches `prototipo/lancamento-rapido` e `prototipo/favoritos`.
- [Dashboards e fechamento do mês](issues/11-dashboards-e-fechamento-do-mes.md): a v1 é um app com abas (Hoje, Mês, Cartões, Histórico, Futuro), com "ainda dá para gastar" em destaque, o fechamento do mês em texto corrido, a comparação por categoria contra o mês anterior e o mesmo mês do ano passado, e o cartão numa linha que abre as compras. Sem pizza: barras e listas bastam. A projeção de saldo mostra duas linhas, só com os previstos e com o que falta do planejamento. Protótipo na branch `prototipo/dashboards`.
- [Exportar o Mobills e medir o histórico](issues/07-exportar-o-mobills-e-medir-o-historico.md): o histórico real tem cerca de 11 mil linhas em 7 anos e 8 meses (6.283 transações com 1 conta só, 0 subcategorias, 4 tags e 311 pendentes, e 4.742 compras em 219 faturas de 7 pastas de cartão), na ordem de poucos MB. As compras de cartão estão no export geral e nas faturas (somar duplica); a fatura traz a data real da compra e o cartão, e o geral traz tags e `(n/total)`.
- [Importação do Mobills](issues/18-importacao-do-mobills-cartao-e-datas.md): o histórico entra pelo cruzamento do export geral com as faturas por cartão e mês (97,7% casam), uma vez só, com a data real da compra e o cartão da fatura e as tags, `(n/total)` e situação do geral, sem digitar datas; o que não casa vai para uma planilha de revisão, que também traz o de-para de categorias e tags e a conferência mês a mês contra os totais do Mobills. O histórico não mexe no saldo (saldo de abertura); os 5 cartões inativos ficam arquivados; `Reajuste de fatura` vira ajuste de fatura. A importação se refaz até a virada, quando a fatura aberta também é exportada. [ADR 0007](../../docs/adr/0007-historico-do-mobills-cruzado-e-sem-saldo.md) e [ADR 0008](../../docs/adr/0008-ajuste-de-fatura-fica-na-fatura.md). Achados da central de ajuda na branch `research/mobills-central-de-ajuda`.
- [Banco de dados e região](issues/09-banco-de-dados-e-regiao.md): Aurora DSQL em sa-east-1 (São Paulo), com o app inteiro nessa região e só os serviços globais em us-east-1; a SCP da organização foi alterada para liberar sa-east-1. O histórico mora numa tabela só, sem agregados nem partições, com o mês em que cada lançamento conta gravado nele, e é guardado para sempre. Sem PITR no DSQL: o backup é a exportação completa diária do app num S3 com versões, 90 dias e Object Lock, na mesma conta. O schema fica no subconjunto do DSQL. [ADR 0009](../../docs/adr/0009-aurora-dsql-em-sao-paulo.md).
- [Como o app roda na AWS](issues/12-como-o-app-roda-na-aws.md): tudo em sa-east-1, sem servidor ligado. A PWA fica num S3 servido pelo CloudFront no endereço padrão (a distribuição nunca é recriada, porque a PWA instalada fica presa a ele); `/api/*` no mesmo endereço vai a uma HTTP API com JWT authorizer e limite de taxa, que chama uma Lambda com a API inteira (FastAPI). O contrato é o OpenAPI gerado pela FastAPI, com os tipos do app gerados dele e conferidos no CI. Login no Cognito por um formulário dentro do app, sem redirecionamento, só senha; refresh token de 10 anos no IndexedDB e token de acesso de 15 minutos. CDK em TypeScript com `prod` e `dev` na mesma conta; deploy e migrations pelo GitHub Actions com OIDC. Backup diário com Object Lock em compliance e teste de restauração no CI; orçamento sem créditos com alertas em US$ 1 e US$ 5; alarmes de backup e de erros. Fora o DSQL, de US$ 0,01 a 0,06 por mês. [ADR 0010](../../docs/adr/0010-app-na-aws-cloudfront-http-api-e-uma-lambda.md); conta configurada pelo [ticket 20](issues/20-configurar-o-acesso-a-conta-aws.md); fatos na branch `research/aws-arquitetura`.
- [Sincronização offline e conflitos](issues/21-sincronizacao-offline-e-conflitos.md): sem internet, só lançamentos um a um (criar, editar, excluir, confirmar previsto); parcelado e recorrente vão como um pedido só, gerados pelo servidor; o aparelho guarda o que é preciso para lançar e a última resposta de cada tela. A fila sai em lote, sem duplicar; o **não enviado** aparece com ⏳ e já conta no aparelho. Mudança sobre os mesmos campos que o outro mudou depois vira **conflito**, decidido campo a campo por quem a fez; campos diferentes entram sozinhos; exclusão vence edição. Aviso de "Parece repetido"; quem criou e quem alterou fica no menu ⋯ > Informações. [ADR 0011](../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md).
- [Sugestão automática de categorias e tags](issues/22-sugestao-automatica-de-categorias-e-tags.md): busca no histórico do casal pelo texto da descrição (a partir de 2 letras, até 3 pacotes de categorias, tags, conta e pessoa, do mais recente ao mais antigo), sem ML nem IA na v1 e funcionando offline com um índice no aparelho; o histórico do Mobills já alimenta desde o dia 1. A spec deixa um contrato de fontes de sugestão para um modelo ou IA futuros, só no servidor e dentro da AWS, com o histórico como plano B.
- [Limite comprometido do cartão](issues/23-limite-comprometido-do-cartao.md): o comprometido soma a fatura aberta, as faturas fechadas não pagas e as parcelas futuras; o disponível é o limite menos ele. O limite é opcional e informado pelo casal (cartão adicional divide o do titular); recorrência não conta. Aparece só na aba Cartões, numa barra na linha do cartão e, no detalhe, com os parcelamentos e uma lista dos próximos 12 meses; sem aviso ao lançar. Na virada, faturas importadas contam como pagas, menos a aberta e as fechadas dentro do vencimento.
- [Busca e filtros salvos](issues/24-busca-e-filtros-salvos.md): tela única de busca com texto livre e filtros combinados, período pela data da compra e filtro Fatura à parte; filtros salvos do casal; edição em lote só de categorias e tags, com prévia, desfazer por 30 dias e só com internet. ([ADR 0013](../../docs/adr/0013-busca-por-data-da-compra-e-fatura-a-parte.md))
- [O que o Mobills exporta](issues/01-o-que-o-mobills-exporta.md): o export é XLSX, em dois modos (todas as transações e só cartão), e as faturas trazem a data real da compra. Achados na branch `research/mobills-exportacao`.
- [Crédito da conta AWS](issues/16-conferir-credito-e-compartilhamento-na-conta-aws.md): saldo de US$ 119,98, válido até 12/04/2027, com o compartilhamento de créditos mantido (o outro projeto consome o mesmo crédito).
- [Exportação](issues/25-exportacao.md): o backup é um zip de CSVs por tabela com manifesto e versão do formato, restaurado só em banco vazio; o CSV da planilha é um arquivo só de lançamentos. Um gerador atende o backup diário, o "exportar tudo" do app (URL assinada) e a carga do histórico do Mobills, que gera um backup válido; o CI testa a ida e volta. Veja o [ADR 0012](../../docs/adr/0012-exportacao-unica-zip-de-csvs-e-restauracao-so-em-banco-vazio.md).
- [Conferir as regras de estorno e ajuste de fatura](issues/94-conferir-as-regras-de-estorno-e-ajuste.md): cancelar é excluir (fatura aberta ou fechada); a compra com estorno não sai; o estorno acompanha a compra; estorno avulso sem compra; alcance "só esta / esta e as próximas / todas" em qualquer campo da parcela; **partes da compra** na v1, à vista, parcelada e recorrente, por proporção. [ADR 0022](../../docs/adr/0022-partes-da-compra.md) e adendo da [ADR 0016](../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md); tickets 133 a 141 (e o 142, pendência do 133).

## Not yet specified


## Out of scope

- Importar extrato ou fatura (OFX/CSV) e Open Finance: na v1 o lançamento é manual.
- Conferência da fatura em lote a partir do arquivo da fatura: o dono já prevê essa funcionalidade para depois da v1.
- Leitura do QR code da nota fiscal (NFC-e), foto de recibo e anexo de comprovante: automação de entrada fica para depois da v1.
- Lançamento por voz ou texto livre com IA: idem.
- Metas e caixinhas; patrimônio e investimentos: não servem para largar o Mobills. O dono prevê lançar os investimentos depois, a partir de planilhas próprias, numa funcionalidade separada; na v1 o saldo é o das contas.
- Comparações corrigidas pela inflação (IPCA): idem.
- Notificações (fatura fechando, planejamento estourando): idem.
- Divisão de despesas do casal ("quem deve a quem"): a pessoa já diz de quem é cada lançamento.
- Dividir um lançamento em partes com tags diferentes: o dono não quer se preocupar com isso agora.
- Dívida com juros calculada pelo app (tabela Price ou SAC): dívidas entram como parcelamento ou recorrência, com os valores já conhecidos.
- Sobra do planejamento que passa para o mês seguinte (envelope acumulado): fica para depois da v1.
- Histórico completo de alterações de um lançamento: na v1 basta saber quem criou e quem alterou por último.
- Recorrência por dia útil ("5º dia útil", "fim de semana vai para segunda") e calendário de feriados: na v1 a recorrência tem dia fixo e a data real se ajusta na confirmação.
- Estimativa que aprende (o previsto da conta de luz usar o último valor confirmado): na v1 o previsto usa o valor da regra.
- Cópia do backup fora da AWS (Drive ou similar): na v1 o backup fica num S3 da mesma conta, com Object Lock, e o "exportar tudo" do app permite baixar uma cópia à mão.
