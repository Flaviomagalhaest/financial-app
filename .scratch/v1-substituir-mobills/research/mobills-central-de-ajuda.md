# Central de ajuda do Mobills: plano, período e o que sai na exportação

Ticket de origem: 18-importacao-do-mobills-cartao-e-datas. Data de acesso de todas as fontes: 2026-10-25.

Pesquisa anterior: [mobills-exportacao.md](mobills-exportacao.md) (2026-10-24), que não conseguiu ler a central de ajuda.

## Como a central foi lida desta vez

A página da central (`/hc/pt-br`) ainda devolve 403 com o desafio da Cloudflare. Eu não contornei essa proteção.

A **API pública do Zendesk Help Center** respondeu 200 sem login e sem truque de navegador. Ela devolve o texto dos artigos publicados, o mesmo que a página mostra. O `robots.txt` do site não bloqueia esses caminhos. Baixei os 164 artigos em pt-br (6 páginas de `articles.json`) e li os que tratam de exportação, backup, planos, cartões, recorrências e LGPD. As capturas de tela dos artigos (`/hc/article_attachments/<id>`) também responderam 200.

Endereços usados:

- Lista: `https://mobills.zendesk.com/api/v2/help_center/pt-br/articles.json?page=N&per_page=30`
- Busca: `https://mobills.zendesk.com/api/v2/help_center/articles/search.json?query=<termo>&locale=pt-br` (termos: exportar, exportação, backup, fatura, planilha, excel, API, relatório, importar)
- Traduções de um artigo: `https://mobills.zendesk.com/api/v2/help_center/articles/<id>/translations.json`

Os links `html_url` citados abaixo são as páginas públicas dos artigos. Num navegador comum eles abrem, mas para robôs devolvem 403.

## Resumo

1. **Plano exigido para exportar.**
   - Plano gratuito e Premium: **não encontrado na fonte oficial.** O artigo de exportação não cita plano nenhum ([fonte A](#fonte-a)). Os artigos de planos não põem a exportação nem na lista do Free nem na do Premium ([fontes D](#fonte-d), [E](#fonte-e) e [F](#fonte-f)).
   - Único texto oficial que liga plano e exportação: no plano da parceria **Wellhub/Gympass**, a central diz "Exportação de dados indisponível" a partir de 14/09 ([fonte B](#fonte-b)). A mesma página diz que "relatórios avançados" são "exclusivos dos Planos Mobills Premium e PRO" ([fonte C](#fonte-c)).
   - Indício, não confirmação: o Free é descrito com limites em "filtros" ([fonte D](#fonte-d)), e a tela de exportação é feita de filtros ([fonte A](#fonte-a)). O blog oficial também lista "Exportar e criar relatórios" entre as funções do Premium (pesquisa anterior, fonte 4). A regra para o Free continua sem fonte oficial.
2. **Limite de período por exportação.**
   - **Web:** "Se optar por exportar transações de anos anteriores, é possível fazer isso de 2 em 2 anos" ([fonte A](#fonte-a)). Leio isso como no máximo 2 anos por arquivo na web. O artigo não dá mais detalhe.
   - **Celular (Android e iOS):** a tela tem "Data inicial" e "Data final" livres. Nenhum limite aparece no texto nem nas capturas ([fonte A](#fonte-a)). Limite no celular: não encontrado na fonte oficial.
   - **Os três modos** "todas as transações", "só cartão de crédito" e "fatura do cartão por mês": **não encontrados na fonte oficial.** A central descreve uma só exportação de transações, com estes filtros: período, categorias, contas, tags, situações e tipos na web; categorias, contas, tipo (todas, despesas ou receitas) e datas no celular ([fonte A](#fonte-a)). Nenhum artigo fala em exportar fatura ou só cartão. Então o limite desses modos também não está na central.
   - Diferença entre plataformas, que pesa na importação: na web saem transações pendentes e efetivadas num só arquivo. No celular saem só "despesas e/ou receitas efetivadas", sem pendentes e sem transferências ([fonte A](#fonte-a)). Formatos: PDF ou XLS na web; PDF, XLS ou CSV no celular.
3. **Backup completo, API, exportação de contas, cartões, recorrências e planejamento.**
   - **Backup completo:** não existe como arquivo. O artigo sobre backup diz que a cópia dos dados é a nuvem, isto é, a versão Web ([fonte G](#fonte-g)).
   - **API pública:** não encontrado na fonte oficial. A busca por "API" na central só achou o artigo de contato com o suporte.
   - **Contas, cartões (limite, fechamento, vencimento), recorrências e planejamento:** não encontrado na fonte oficial. A exportação descrita é só de transações ([fonte A](#fonte-a)). A central confirma que esses dados existem no app: o cartão guarda limite, data de fechamento, data de pagamento e conta associada ([fonte H](#fonte-h)), e existem transações fixas e repetidas ([fonte I](#fonte-i)). Mas nenhum artigo diz que eles saem num arquivo.
   - **Caminho por pedido (LGPD):** a central lista o direito à "Portabilidade" e dá o e-mail do encarregado de dados ([fonte J](#fonte-j)). Formato, prazo e escopo não estão publicados.

## Detalhes e fontes

### Fonte A: "Como exportar minhas transações do Mobills?" {#fonte-a}

- URL: <https://mobills.zendesk.com/hc/pt-br/articles/360051811854-Como-exportar-minhas-transa%C3%A7%C3%B5es-do-Mobills> (lida pela API: `.../api/v2/help_center/pt-br/articles/360051811854.json`). Atualizado em 2026-10-17; texto editado em 2024-12-03.
- Aviso no topo: "Agora é possível exportar a situação das transações em um só arquivo. Isso mesmo, é possível exportar transações tanto pendentes, como efetuadas. No momento essa implementação está disponível somente na Plataforma Web."
- Celular: "Nas versões mobile, ainda estamos com o modelo antigo, ou seja, considera apenas despesas e/ou receitas efetivadas, não exportando transações pendentes e transferências."
- Moeda: "A exportação para transações convertidas em outras moedas são realizadas com base na cotação no dia do cadastro da transação."
- Celular (iOS e Android): "toque nos três pontinhos do canto inferior direito e depois em 'Exportar relatórios'"; depois "escolha as categorias, contas, o tipo de conta (todas, despesas ou receitas) e a data inicial e final". As capturas mostram os botões PDF, XLS e CSV e a nota "O relatório considera apenas despesas e/ou receitas efetivadas, sem transferências."
- Web: "clique nos 3 pontinhos, em 'Mais opções' e escolha 'Exportar transações'"; depois escolha "as categorias, as contas, o tipo da conta (receita ou despesa) e o período" e o formato, "PDF ou XLS".
- A captura da web (anexo 31504651429915) mostra o painel "Exportar Transações" com os campos De, Até, Categorias, Contas, Tags, Situações e Tipos, e os botões PDF e XLS. A captura não abre a lista "Tipos", então não dá para saber se há opção de cartão.
- Limite de período (web): "Se optar por exportar transações de anos anteriores, é possível fazer isso de 2 em 2 anos. Sempre que for selecionar o período do ano na web, irá aparecer os anos anteriores para selecionar."
- Aviso: "A funcionalidade de exportação está passando por algumas mudanças, e você poderá notar algumas diferenças no arquivo quando exportado em diferentes plataformas, mobile e web."
- Plano: o artigo não cita Free, Premium nem PRO.
- Traduções do mesmo artigo (en-us de 2023-10-18, es de 2024-08-29): versões antigas, com o mesmo aviso de "only paid expenses and/or receipts, not exporting pending transactions or transfers" e formatos "PDF", "XLS" ou "CSV". Também não citam plano nem limite de período.

### Fonte B: "Atualização nos planos através da parceria com Wellhub/Gympass" {#fonte-b}

- URL: <https://mobills.zendesk.com/hc/pt-br/articles/54745604067739-Atualiza%C3%A7%C3%A3o-nos-planos-atrav%C3%A9s-da-parceria-com-Wellhub-Gympass>. Criado em 2026-08-21; atualizado em 2026-10-25.
- "O que muda a partir de 14/09: [...] Exportação de dados indisponível e anexos limitados a 1."
- "Nada será apagado! Todo o seu histórico será mantido."
- "Como manter todos os recursos? Faça upgrade para o Mobills Premium."
- Vale só para o plano da parceria Wellhub/Gympass. Não diz nada sobre o plano Free comum.

### Fonte C: "Mobills + Wellhub (Gympass)" {#fonte-c}

- URL: <https://mobills.zendesk.com/hc/pt-br/articles/360055238013-Mobills-Wellhub-Gympass>. Atualizado em 2026-10-07.
- O que o plano Wellhub inclui: "Registro de transações, calendário financeiro e importação de dados"; "Uso de tags, filtros, subcategorias e gráficos". A exportação não está na lista.
- "Recursos avançados (como sincronização bancária automática ilimitada, relatórios avançados e criação ilimitada de contas/cartões) são exclusivos dos Planos Mobills Premium e PRO."

### Fonte D: "O Mobills é gratuito ou pago?" {#fonte-d}

- URL: <https://mobills.zendesk.com/hc/pt-br/articles/360051144493-O-Mobills-%C3%A9-gratuito-ou-pago>. Atualizado em 2026-10-20.
- "O Mobills é gratuito, porém, com algumas limitações de funcionalidades [...] como adicionar mais de um cartão de crédito, gráficos detalhados, filtros, etc." A exportação não é citada.

### Fonte E: "Como posso assinar o Mobills?" {#fonte-e}

- URL: <https://mobills.zendesk.com/hc/pt-br/articles/360024891434-Como-posso-assinar-o-Mobills>. Atualizado em 2026-08-19.
- Planos: "Mobills Free: Acesso limitado às funcionalidades"; "Mobills Premium Mensal: Acesso total ao Mobills durante 30 dias"; "Mobills Premium Anual: Acesso total ao Mobills durante 365 dias". Não detalha a exportação.
- Outro artigo, "Tudo sobre o Mobills PRO" (<https://mobills.zendesk.com/hc/pt-br/articles/39727734628251-Tudo-sobre-o-Mobills-PRO>), lista o que o Premium oferece: Open Finance, planejamentos e objetivos, "Cadastro ilimitado de contas e cartões", "gráficos e relatórios detalhados", App e Web. A exportação também não aparece nessa lista.

### Fonte F: "Se minha assinatura expirar, meus dados serão perdidos?" {#fonte-f}

- URL: <https://mobills.zendesk.com/hc/pt-br/articles/17205735261211-Se-minha-assinatura-expirar-meus-dados-ser%C3%A3o-perdidos>. Atualizado em 2026-10-05.
- No Free, "os seus históricos de transações [...] estarão guardados e não serão perdidos", mas há limites "como o gerenciamento de dois ou mais cartões de crédito e de quatro ou mais contas bancárias". A exportação não é citada.
- A página de planos do site (<https://www.mobills.com.br/pricing/>) compara "Mobills Free R$ 0" ("Categorias de despesas e receitas", "Sincronização uma vez ao dia") com o Premium ("Cadastro de contas ilimitado", "Importe dados financeiros", "Tags / etiquetas", "Filtros personalizados" etc.). Ela também não cita exportação.

### Fonte G: "Perdi meus dados, é possível ter um backup?" {#fonte-g}

- URL: <https://mobills.zendesk.com/hc/pt-br/articles/1260804532789-Perdi-meus-dados-%C3%A9-poss%C3%ADvel-ter-um-backup>. Atualizado em 2026-10-23.
- O artigo chama de "nosso servidor principal na nuvem" a versão Web do Mobills, e diz: "tudo que colocar e estiver na web certinho deve estar armazenado na nossa nuvem."
- Não oferece arquivo de backup nem restauração. Se os dados se perderam, a orientação é "seguir o controle, registrando seus dados a partir de hoje normalmente."

### Fonte H: "Como criar um cartão de crédito manual?" {#fonte-h}

- URL: <https://mobills.zendesk.com/hc/pt-br/articles/360049719974-Como-criar-um-cart%C3%A3o-de-cr%C3%A9dito-manual>. Atualizado em 2026-10-15.
- "Ao criar um cartão é obrigatório inserir as informações de Descrição, Limite, Data do Fechamento, Data do Pagamento e Conta associada." A bandeira é opcional.
- Mostra que o app guarda esses campos. Não diz que eles saem na exportação.

### Fonte I: "O que são transações fixas ou repetidas?" {#fonte-i}

- URL: <https://mobills.zendesk.com/hc/pt-br/articles/360052154234-O-que-s%C3%A3o-transa%C3%A7%C3%B5es-fixas-ou-repetidas>. Atualizado em 2026-10-11.
- Fixa: "serão criados lançamentos iguais todos os meses da data escolhida em diante." Repetida: "você escolherá quantas vezes essa despesa se repetirá", com repetição "Diário, Semanal, Mensal e Anual".
- Não diz se a regra da recorrência sai num arquivo.

### Fonte J: "Como posso exercer meus direitos?" (LGPD) {#fonte-j}

- URL: <https://mobills.zendesk.com/hc/pt-br/articles/4403518248091-Como-posso-exercer-meus-direitos>. Atualizado em 2025-07-24.
- "Portabilidade: Você tem o direito de solicitar a migração das suas informações pessoais para outra organização."
- Contato do encarregado de dados: `privacidade@toroinvestimentos.com.br`. A empresa que publica o app na App Store é a "Toro Investimentos Ltda.".

### Fonte K: descrições nas lojas {#fonte-k}

- Google Play (<https://play.google.com/store/apps/details?id=br.com.gerenciadorfinanceiro.controller&hl=pt_BR>): fala em "Relatórios super dinâmicos" e "Acesso multiplataforma (Web, Android e IOS)". Não cita exportação, backup nem API.
  - Cuidado: a página da Play tem o texto "Exportar para arquivo CSV / Excel. Faça backup ou imprima...", mas ele é de outro app que a loja sugere (`com.ktwapps.walletmanager`). Eu descartei esse texto.
- App Store (`id921838244`, lido pela API pública de busca do iTunes, `itunes.apple.com/search?term=mobills&country=br`): "Com Mobills Premium você tem acesso à integrações automáticas com os principais bancos" e "Relatórios simples e dinâmicos". Não cita exportação. Versão 6.24.0, de 2026-10-23.

### Outros artigos lidos que não falam de exportação

Visualizar fatura (30158978834843), agrupar despesas do cartão (360049423534), gráficos de cartões (360051548434), gráficos de despesas e receitas (360049912794), limite do cartão (360051954994), integração bancária (20259960349339), excluir conta (360055350173), reiniciar conta (360052326734). Nenhum deles cita exportação, backup em arquivo ou API.

## O que foi tentado e falhou

| Tentativa | Resultado em 2026-10-25 |
|---|---|
| `curl` em `https://mobills.zendesk.com/hc/pt-br` | 403, página "Just a moment..." da Cloudflare. Não contornei. |
| `curl` em `https://ajuda.mobills.com.br/hc/pt-br` | 301 para `https://mobills.zendesk.com:443/hc/pt-br`, que dá 403. |
| `WebFetch` no artigo 360051811854 (página HTML) | 403 Forbidden. |
| `WebSearch` "site:ajuda.mobills.com.br exportar" | Nenhum resultado do domínio do Mobills. |
| `WebSearch` "mobills exportar transações excel premium gratuito" e variações com "Reclame Aqui" | Nenhum resultado sobre o Mobills. Então não há nem fonte secundária sobre o plano. |
| `https://mobills.zendesk.com/api/v2/help_center/articles.json` (sem idioma) | 301 para a versão `pt-br`, que funcionou. |
| `https://mobills.zendesk.com/api/v2/help_center/articles/360051811854/attachments.json` | 301 sem corpo. As imagens abriram direto por `/hc/article_attachments/<id>` (200). |
| `https://mobills.zendesk.com/api/v2/community/posts/search.json?query=exportar` | 404 `RecordNotFound`: a central não tem comunidade pública. |
| `https://mobills.zendesk.com/hc/api/internal/help_center_translations.json` | 401: área interna, não insisti. |
| `https://apps.apple.com/br/app/mobills-controle-financeiro/id1035436307` | 404 (id errado). O id certo (921838244) veio da API de busca do iTunes. |
| `https://www.mobills.com.br/premium/` | 404. |
| `WebFetch` na página da Google Play | Conteúdo truncado. Li a descrição pelo HTML baixado com `curl` (200). |

O que funcionou: a API pública do Help Center (200 em lista, busca, traduções e categorias), as capturas dos artigos (200), a página de planos (200), a página da Google Play (200) e a API de busca do iTunes (200).

## Lacunas

- Plano exigido para exportar no Free e no Premium comuns: a central não diz. Só há a regra do plano Wellhub ("indisponível").
- Existência e limite de período dos modos "só cartão de crédito" e "fatura do cartão por mês": não aparecem na central. Se o dono viu esses modos no app, eles são mais novos que o artigo ou estão dentro do filtro "Tipos" da web, que a central não detalha.
- Limite de período no celular.
- Exportação de contas, cartões, recorrências e planejamento, e qualquer API.

## Próximos passos sugeridos

1. Pedido ao dono (HITL): abrir o painel "Exportar Transações" na web, abrir a lista "Tipos" e anotar as opções. Tentar também um período maior que 2 anos e anotar a mensagem que aparece.
2. Pedido ao dono (HITL): anotar em qual plano a conta estava quando exportou. Se puder, ver se o botão de exportar aparece numa conta Free.
3. Como a central não mostra exportação de cartões, a importação deve tirar limite, fechamento e vencimento de outro lugar: digitação no app novo, ou dedução a partir das datas das faturas no XLSX.
