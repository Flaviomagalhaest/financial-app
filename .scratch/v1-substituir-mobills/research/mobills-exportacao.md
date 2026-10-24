# O que o Mobills exporta

Ticket de origem: [01-o-que-o-mobills-exporta](../issues/01-o-que-o-mobills-exporta.md). Data de acesso de todas as fontes: 2026-10-24.

## Resumo

**Resultado geral: a pesquisa ficou incompleta.** A central de ajuda oficial (`ajuda.mobills.com.br`, que redireciona para `mobills.zendesk.com/hc/pt-br`) é protegida por desafio anti-robô da Cloudflare ("Just a moment...") e respondeu 403 ao `curl`; o `WebFetch` não resolveu o host. Eu não contornei essa proteção. Sem a central de ajuda, não há fonte primária acessível com os campos de cada exportação. Só o site institucional, o blog oficial da Mobills e os termos de uso estavam acessíveis, e eles dizem muito pouco sobre exportação.

Respostas ao "Levantar" do ticket:

1. **Onde fica a exportação e qual plano exige.**
   - Onde: não encontrado na fonte oficial. O blog oficial só diz que existe "exportação de relatórios" no app, sem dizer em que tela ([fonte 3](#fonte-3)).
   - Plano: indício de que é do Premium. O blog oficial lista "Exportar e criar relatórios" entre as funções do Mobills Premium ([fonte 4](#fonte-4)). Não encontrado na fonte oficial: confirmação na central de ajuda ou na página de planos.
   - A página de planos lista só quatro benefícios do Premium e não cita exportação ([fonte 2](#fonte-2)).
   - O Premium é válido em iOS, Android e Web; a assinatura anual custa R$ 99,90 ou 12 x R$ 9,90 ([fonte 2](#fonte-2)). Outro post do mesmo blog mostra "R$ 19,90 por mês" ([fonte 5](#fonte-5)), então o preço mudou entre as páginas e não deve ser tomado como definitivo.
2. **Formatos e limite de período.**
   - Formatos: Excel, PDF e CSV, segundo o blog oficial, que diz "exportação de relatórios" ([fontes 3](#fonte-3) e [5](#fonte-5)). OFX aparece só como formato de leitura (importação) ([fonte 3](#fonte-3)).
   - Backup do app: não encontrado na fonte oficial.
   - Limite de período por exportação: não encontrado na fonte oficial.
3. **Campos de cada exportação** (lançamentos, transferências, contas e saldos, cartões e faturas, parcelas, recorrências, planejamento): **não encontrado na fonte oficial**, item por item. O blog fala apenas de "relatórios", sem listar colunas.
   - O blog oficial confirma que o Mobills tem "Categorias, Subcategorias e Tags" ([fonte 3](#fonte-3)). Isso é recurso do app, não prova que a exportação traga esses campos.
4. **API, backup completo ou outra forma de tirar os dados.**
   - API pública: não encontrado na fonte oficial.
   - Backup completo: não encontrado na fonte oficial.
   - Caminho jurídico (LGPD): o aviso de privacidade diz que o titular pode "solicitar a migração das suas informações pessoais para outra organização" (portabilidade), entrando em contato com a empresa ou com o encarregado de dados ([fonte 1](#fonte-1)). O aviso não diz formato, prazo nem escopo.
5. **Limitações conhecidas (o que não sai).** Não encontrado na fonte oficial.

Efeito nas decisões que esperam por este ticket (04, 07 e a importação): nenhuma delas pode se apoiar nesta pesquisa para saber os campos. A exportação real tem de ser examinada pelo dono (ver "Próximos passos").

## Detalhes e fontes

### Fonte 1: Aviso de privacidade (portabilidade) {#fonte-1}

- URL: <https://www.mobills.com.br/privacidade-e-termos/aviso-de-privacidade/>
- Trecho: "Portabilidade: Você tem o direito de solicitar a migração das suas informações pessoais para outra organização." Também: "os dados pessoais são seus e você poderá acessá-los a qualquer momento", com o contato do encarregado de dados por e-mail.
- Uso aqui: só mostra que há um caminho por solicitação, baseado na LGPD (Lei nº 13.709/2018). Não descreve a exportação do app.

### Fonte 1b: Termos de uso {#fonte-1b}

- URL: <https://www.mobills.com.br/privacidade-e-termos/termos-de-uso/> (acessível também em <https://www.mobills.com.br/termosdeuso/>; a URL <https://www.mobills.com.br/termos-de-uso> devolve 404).
- Trechos relevantes: existe "o plano básico gratuito ou o plano pago através de uma assinatura mensal ou anual"; "os serviços disponibilizados em cada plano poderão ser alterados", com aviso prévio; o usuário é "o único responsável por todos os dados e informações que inserir em sua conta".
- Os termos não mencionam exportação, backup, API nem formato de dados (busca por "export", "backup", "formato" e "portabilidade" só achou a menção a "formato de uma venda parcelada", sem relação).
- Não encontrado na fonte oficial: o que acontece com os dados ao cancelar a conta (a página de planos só diz que assinar ou não "não impacta os dados cadastrados").

### Fonte 2: Página de planos {#fonte-2}

- URL: <https://www.mobills.com.br/pricing/>
- Benefícios do Premium listados: controle de todos os cartões de crédito; planejamento financeiro; "acesso à relatórios mensais"; "todas as funções Mobills Premium". Não cita exportação, formato nem backup.
- "A assinatura Premium ... é válida para todas as plataformas, iOS, Android e/ou Web."
- "A assinatura Premium ou a falta dela não impactam nos dados cadastrados na plataforma." Ou seja, os dados ficam mantidos sem o Premium; isso não diz se a exportação continua disponível sem ele.
- Preço na página: R$ 99,90 por ano ou 12 x R$ 9,90.

### Fonte 3: Blog oficial, "Apps de controle financeiro" {#fonte-3}

- URL: <https://www.mobills.com.br/blog/aplicativos/apps-de-controle-financeiro/>
- Na seção sobre o próprio Mobills ("Funcionalidades e vantagens"): "Leitura de SMS, QRCode, excel e OFX"; "Categorias, Subcategorias e Tags"; "Exportação de relatórios pra Excel, PDF ou CSV"; "Sincronização dos dados multiplataforma na nuvem"; "Acessível para Android, iOS e Web".
- Observação: é texto de marketing do próprio Mobills, sem detalhe técnico. As linhas de "Backup automático" e "exportação de transações para impressão" da mesma página pertencem a outros aplicativos (Orçamento Fácil e Money Lover), não ao Mobills, e foram descartadas.

### Fonte 4: Blog oficial, "Mobills é seguro?" {#fonte-4}

- URL: <https://www.mobills.com.br/blog/aplicativos/mobills-e-seguro/>
- Na lista de funções do Mobills Premium: "Exportar e criar relatórios para um melhor gerenciamento". A versão gratuita é descrita com limites (1 cartão, lançamentos limitados), sem citar exportação.

### Fonte 5: Blog oficial, "Software de gestão financeira" {#fonte-5}

- URL: <https://www.mobills.com.br/blog/financas-pessoais/software-de-gestao-financeira-gratuito/>
- "Possibilidade de exportar relatórios para Excel ou PDF., além do CSV". A mesma página cita "R$19,90 por mês" para o Premium.

### Tentativas que falharam

| Fonte | Resultado em 2026-10-24 |
|---|---|
| `https://ajuda.mobills.com.br/hc/pt-br` e a busca `?query=exportar` | Redireciona para `mobills.zendesk.com`; `curl` recebe 403 e a página "Just a moment..." da Cloudflare. Não contornei. |
| `https://mobills.zendesk.com/api/v2/help_center/pt-br/articles/search.json` | 404 `RecordNotFound`. |
| `WebFetch` em `ajuda.mobills.com.br` e `mobills.zendesk.com` | Falha de DNS (`ENOTFOUND`) no ambiente. |
| `https://www.mobills.com.br/recursos/` | 403. |
| `https://web.archive.org` | Conexão recusada pelo proxy do ambiente; além disso, cópia de terceiros não seria fonte primária. |
| Busca no site (`wp-json/wp/v2/search`) por "exportar", "backup", "importar" | Só posts genéricos; nenhum artigo oficial de ajuda sobre exportação. |
| Tela de exportação do app | Não acessada: exigiria a conta real do dono, vetada nesta tarefa. |

## Lacunas

- Todos os campos das exportações (lançamentos, transferências, contas, saldos, cartões, faturas, parcelas, recorrências, planejamento).
- Se parcelas saem como uma linha por parcela e se há vínculo entre elas.
- Em qual fatura cai uma compra no cartão, e se a data da compra sai.
- Local exato da exportação (app, web) e plano exigido, confirmados na central de ajuda.
- Limite de período por exportação.
- Existência de backup completo, API ou integração para tirar os dados.
- Limitações conhecidas.

## Próximos passos sugeridos

1. Abrir a central de ajuda num navegador comum e buscar "exportar", "relatório", "backup" e "importar" (a Cloudflare só deixa passar navegador humano). Copiar os títulos e links dos artigos para um novo registro de pesquisa.
2. Pedido ao dono (HITL, ligado ao ticket 07): fazer uma exportação de teste no app web e no celular, com período curto, e registrar só a forma dos dados (nomes das colunas, formatos, se há uma linha por parcela, como o cartão e a fatura aparecem), sem valores reais no repositório.
3. Se a exportação do app for insuficiente, avaliar o pedido de portabilidade pela LGPD ao encarregado de dados (fonte 1), sabendo que formato e prazo não estão publicados.
