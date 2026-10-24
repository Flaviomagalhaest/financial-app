# Lacunas de plataforma e banco: respostas de fontes primárias

Acesso a todas as fontes: 2026-10-24. A numeração `[Sx]` é só deste arquivo (não reaproveita os códigos de `app-web-instalavel.md` nem de `banco-de-dados-aws.md`). Convenções: "não encontrado na fonte oficial" = a fonte lida não diz; `[inferência]` = conclusão minha. Não repeti fontes já lidas nas pesquisas anteriores, só as citei quando precisei de uma frase nova delas.

---

## Plataforma

### 1. Desligar "Abrir como App Web" no iOS 26 e a isenção do ITP de 7 dias

- O WebKit descreve a mudança do iOS 26 e iPadOS 26: "por padrão, todo site adicionado à Tela de Início abre como app web". O usuário pode desligar "Open as Web App" ao adicionar, e então o que ele cria é um "bookmark para o navegador", **mesmo que o site esteja configurado como app web** `[S1]`.
- A mesma página diz que a mudança não remove nenhum suporte atual do WebKit a recursos de app web, e que com manifesto os benefícios do manifesto continuam `[S1]`. Também diz que agora "não há requisitos de instalabilidade" no Safari (qualquer site pode virar app web) `[S1]`.
- A isenção do ITP é escrita assim: o domínio de primeira parte dos **home screen web applications** fica isento do limite de 7 dias sobre todo armazenamento gravável por script (o ITP "sempre pula esse domínio" no algoritmo de remoção), e os dados do app web ficam **isolados do Safari**, sem serem afetados pela classificação de rastreamento feita no Safari `[S2]`.
- O que o ITP apaga após 7 dias sem interação com o site: cookies criados por JavaScript e armazenamento gravável por script: IndexedDB, LocalStorage, media keys, SessionStorage, registros e cache de Service Workers `[S2]`.
- Não encontrado na fonte oficial: texto que diga explicitamente que um bookmark criado com "Open as Web App" desligado perde a isenção. A página do ITP `[S2]` não menciona iOS 26, "Open as Web App" nem "bookmark" (busca no texto da página: sem ocorrências), e a página do Safari 26 `[S1]` não menciona ITP nesse trecho.
- `[inferência]` Com a opção desligada, o ícone é um bookmark que abre no Safari, ou seja, não é um "home screen web application"; portanto o site cai na regra geral de 7 dias sem interação (inclui IndexedDB/SQLite-WASM). Isso decorre da leitura conjunta de `[S1]` e `[S2]`, mas nenhum dos dois diz com essas palavras. A opção vem **ligada por padrão** `[S1]`, então o risco é o usuário desligar sem querer; reverter exigiria remover o ícone e adicionar de novo (como a opção é escolhida "ao adicionar" `[S1]`; se dá para trocar depois: não encontrado na fonte oficial).

### 2. O ITP de 7 dias vale no WKWebView de um app Capacitor/nativo?

- O WebKit diz que, desde iOS 14.0 e macOS Big Sur, o ITP "está habilitado por padrão em **todos** os apps WKWebView" `[S3]`.
- Esse post cita só o ITP em geral: o texto da regra de 7 dias vem de `[S2]` ("7 dias sem interação do usuário com o site"). Não encontrado na fonte oficial: texto que diga que o limite de 7 dias de armazenamento se aplica (ou não) a conteúdo local carregado por um app (esquema próprio/arquivo local) dentro do WKWebView.
- "App-Bound Domains" **não** desliga o ITP: é um recurso à parte, em que o app lista até 10 domínios na chave `WKAppBoundDomains` do Info.plist, e `limitsNavigationsToAppBoundDomains = YES` na configuração do web view restringe a navegação a esses domínios e libera APIs (injeção de JavaScript, cookies, message handlers) `[S3][S4]`. Conteúdo local (arquivos, data URLs, strings) conta sempre como app-bound `[S3]`. O post não diz que isso afeta a regra de 7 dias.
- O que **desliga** o ITP: o usuário pode desligá-lo nos Ajustes do app se o app declarar `NSCrossWebsiteTrackingUsageDescription` no Info.plist. A configuração "não pode ser lida nem alterada por chamadas de API" `[S3]`. Ou seja, o app não consegue se isentar sozinho.
- `WKWebsiteDataStore`: a página da Apple diz que o armazenamento padrão grava dados "persistentemente em disco", que se pode criar um data store não persistente e que existe data store persistente por identificador ("profile") `[S5]`. Não encontrado na fonte oficial: menção de ITP ou prazo de expiração nessa página `[S5]`. O termo `limitInBrowserApps` não aparece nas fontes lidas (parece nome incorreto; o que existe é `limitsNavigationsToAppBoundDomains` `[S4]`).
- Capacitor: a documentação diz que `localStorage` e IndexedDB em web views "serão eventualmente perdidos" porque o SO recupera espaço dos web views quando falta armazenamento (IndexedDB "pelo menos no iOS"); a **Preferences API** nativa "evita" esses problemas, mas serve só para pouco dado chave/valor, sem consulta `[S6]`. A página não cita ITP nem os 7 dias `[S6]`.
- `[inferência]` Para um app Capacitor, o risco documentado é o de despejo por falta de espaço `[S6]`; se o ITP de 7 dias também apaga o IndexedDB de um app que roda conteúdo local, a fonte oficial não diz. Se o dado só existir no WebView, é seguro tratar o risco como real até testar num aparelho. Dados que precisam durar devem ir para armazenamento nativo (por exemplo Preferences, ou um plugin SQLite nativo) ou para o servidor.

### 3. Expo: build de release com conta Apple gratuita

- Conta gratuita (Personal Team no Xcode): até 10 App IDs e 3 dispositivos, todos expirando em 7 dias, até 3 apps por aparelho; **os provisioning profiles que permitem instalar no aparelho expiram 7 dias depois da emissão**, e é preciso recompilar e reinstalar `[S7]`.
- Build de **release local**: `npx expo run:ios --configuration Release` compila em modo de produção; o Expo diz que esse build "não é assinado automaticamente para envio à App Store" e que serve para testar bugs que só aparecem em produção `[S8]`. A documentação de desenvolvimento local diz o mesmo (builds de produção, "não assinados", não podem ser enviados às lojas) `[S9]`.
- Instalar em aparelho: `npx expo run:ios --device` assina para desenvolvimento, instala e abre o app, desde que haja perfis de desenvolvedor configurados no computador (se não houver, configurar no Xcode, "Setup Xcode signing") `[S8]`.
- O Expo afirma que "compilar localmente" (sem conta Expo) é "a única forma de instalar um **development build** em um iPhone sem conta paga da Apple" `[S10]`. Isso é dito para *development build*; para build de **release** com conta gratuita, a documentação do Expo não diz que funciona nem que não funciona. Não encontrado na fonte oficial.
- O guia de release local do Expo, para iOS, manda usar o Xcode (assina e envia ao App Store Connect) `[S13]`, caminho que pressupõe conta do programa.
- **EAS Build (nuvem):** a documentação exige conta de US$ 99 do Apple Developer Program para criar builds de release para a App Store `[S11]`; distribuição interna por provisioning ad hoc "exige conta paga" e vale para até 100 iPhones por ano `[S12]`. Portanto, com conta gratuita, EAS não resolve instalar no iPhone.
- `[inferência]` Com conta gratuita é possível, numa máquina Mac com Xcode, compilar o app em Release (`--configuration Release --device`) e instalar no iPhone; ele expira em 7 dias `[S7]` e teria de ser reinstalado toda semana. EAS na nuvem e TestFlight/ad hoc ficam fora (conta paga). O limite de 3 dispositivos `[S7]` cobre os 2 usuários. Não verifiquei na prática se o Release assinado de desenvolvimento passa pelo Xcode atual com Personal Team.

### 4. Verificação de desenvolvedores do Android e APK direto (sideload) no Brasil

**O que cada página diz**

| Página (data) | Alcance |
|---|---|
| Visão geral `[S14]` (sem data na página) | "Efetivo em 30 de setembro de 2026": proteções para quem instala apps de **lojas participantes** em regiões selecionadas, em dispositivos Android certificados; expansão global em 2027. |
| Guia `[S16]` (atualizada 2026-08-18) | Proteções "entram no ar" em **Brasil, Indonésia, Singapura e Tailândia** em 30/09/2026. O sistema verifica instalações vindas das lojas Google Play, Honor App Market, OPPO App Market, Samsung Galaxy Store, Transsion Palm Store, vivo V-Appstore e Xiaomi GetApps; em 2027 vira global para todos os apps em dispositivos certificados; "em breve" expande a todas as lojas de terceiros. A tabela de opções diz que, para "sideload de apps não registrados", o caminho é o **fluxo avançado** e que "seus apps ainda podem ser instalados por sideload". |
| FAQ `[S15]` (item de 2026-07-15; página atualizada 2026-09-30) | "O prazo de 30/09/2026 só vale para as lojas participantes". Se o usuário instala o APK **direto (sideload)** ou usa outra loja, "esses requisitos de verificação **não se aplicam ainda**"; recomenda concluir a verificação antes do lançamento global de 2027. |
| Conta limitada `[S17]` (atualizada 2026-10-23) | "As proteções entram em vigor em Brasil, Indonésia, Singapura e Tailândia em 30 de setembro. Qualquer nome de pacote **não registrado** nessa data **não poderá mais ser instalado** em dispositivos Android certificados dessas regiões." Não menciona lojas nem sideload nessa frase. |

**Reconciliação**

- `[inferência]` As quatro páginas só são compatíveis se a frase de `[S17]` for lida como resumo curto da regra de `[S16]`: o bloqueio vale para instalações a partir das lojas participantes; sideload direto continua permitido até 2027 `[S15]`, e depois dele (ou para o app não registrado, quando a regra chegar ao sideload) pelo fluxo avançado `[S15][S16]`. O texto de `[S17]` sozinho dá a entender o contrário, e é mais recente (2026-10-23) que o item do FAQ sobre sideload (2026-07-15). **Não encontrado na fonte oficial** uma frase que resolva a divergência; a página mais recente é `[S17]`.
- Datas e países: efetivo em 2026-09-30 no Brasil (lojas participantes) `[S14][S16]`; global em 2027, sem data exata nas páginas lidas `[S14][S15][S16]`. Os países sancionados ficam de fora: as verificações "não rodam" em dispositivos fisicamente nesses países `[S15]`.
- Escopo técnico: dispositivos Android certificados com Android 7 ou superior `[S15]`; só celular e tablet nas regiões selecionadas `[S15]`.

**Exceções e caminhos para um app de uso pessoal**

- **ADB**: instalar via `adb` não exige verificação e não tem a espera de 24 horas `[S15]`.
- **Conta de distribuição limitada**: grátis, sem documento de identidade, registra apps e permite compartilhar com **até 20 dispositivos** autorizados pelo usuário via QR code ou link; exige conta Google com verificação em duas etapas, perfil de pagamentos do Google, e-mail de contato `[S17]`. Pode migrar para conta plena, não o contrário `[S15]`. A conta plena custa US$ 25 e exige verificação de identidade `[S15][S16]`.
- **Fluxo avançado** (lançado em agosto de 2026): ativar o modo de desenvolvedor, confirmar que ninguém está orientando o usuário, reiniciar e reautenticar, esperar **24 horas** (uma vez) e confirmar com biometria ou PIN; depois pode instalar de desenvolvedores não verificados, liberando por **7 dias ou indefinidamente**, com aviso "Instalar mesmo assim" `[S15]`. Não precisa manter o modo de desenvolvedor ligado depois `[S15]`. Atualizações de apps não registrados só funcionam com o fluxo avançado ativo ou por ADB `[S15]`.
- "Modo de desenvolvedor/conta limitada" como isenção do registro: o modo de desenvolvedor é só um passo do fluxo avançado `[S15]`; a conta limitada registra o app em vez de isentá-lo `[S17]`.
- Para o caso do casal (2 aparelhos, no Brasil): `[inferência]` a conta limitada cobre 2 aparelhos com folga (limite 20) e custo zero `[S17]`; PWA instalada pelo Chrome não passa por essa regra (o texto trata de instalação de pacotes de apps, não de PWAs; a fonte oficial não diz nada sobre PWA/WebAPK nas páginas lidas).

---

## Banco

### 5. Tempo de retomada do Aurora DSQL após Idle/Inactive

- A documentação oficial do ciclo de vida diz que o cluster vira **Idle** depois de um tempo sem conexão e **Inactive** depois de um período mais longo, quando "os recursos em execução são escalados a zero, preservando os dados" `[S18]`.
- Ao conectar a um cluster Idle ou Inactive, o DSQL volta a **Active** automaticamente; "a primeira tentativa de conexão a um cluster Idle ou Inactive será mais lenta que o normal"; para Inactive, "o tempo de restauração depende do tamanho do cluster" `[S18]`.
- **Não encontrado na fonte oficial: número de segundos**, nem os limites de tempo (quanto tempo até Idle e até Inactive). Também não encontrei nas páginas de preço, no FAQ, nem nos posts de conexão e de pool do blog de banco de dados da AWS `[S25][S26]`. Uma busca restrita a domínios AWS tampouco trouxe um número.
- Os "cerca de 15 segundos" (30 s ou mais após mais de 24 h) são do **Aurora Serverless v2**, outro produto (veja a pergunta 7); não devem ser usados para o DSQL `[S22]`.
- Backups só podem ser tomados com o cluster **Active**; em Idle ou Inactive a chamada falha com `FailedPrecondition` até alguém conectar `[S18]`. Backups anteriores continuam válidos `[S18]`. Para um app de 2 usuários, isso interage com o backup agendado: um cluster parado pode não gerar backup `[inferência]` (a documentação não diz se o plano agendado do AWS Backup acorda o cluster).

### 6. PITR no DSQL

- A página de backup do DSQL descreve **só** a integração com o AWS Backup: backups de cluster completo ("complete copies"), agendamento automático e retenção, cópia entre regiões e contas, vault WORM; a restauração **sempre cria um novo cluster** `[S19]`. A página não cita PITR nem restauração para um instante `[S19]`.
- A tabela de disponibilidade de recursos do AWS Backup mostra, para Amazon Aurora DSQL: cópia entre regiões e entre contas sim; **backup incremental** não; **backup contínuo e restauração a um ponto no tempo (PITR)** não (célula vazia); gerenciamento completo sim; cópia a armazenamento frio (lifecycle) sim; vault com isolamento lógico sim. Para Amazon Aurora (provisionado/Serverless v2), a mesma coluna de PITR está marcada `[S20]`.
- A lista de serviços com backup contínuo/PITR do AWS Backup cita S3 e RDS/Aurora e não menciona o DSQL (busca no texto: zero ocorrências de "DSQL") `[S21]`.
- Conclusão sustentada pela fonte: no DSQL não há PITR documentado; só snapshots completos do AWS Backup `[S19][S20][S21]`. Frequência mínima do agendamento e retenção máxima: não encontrado nas páginas lidas (não abri o guia do AWS Backup para isso).
- A tabela de regiões do AWS Backup marca o suporte ao DSQL como disponível em us-east-1 e em sa-east-1 `[S20]`.
- DSQL está na lista de endpoints com `sa-east-1` (São Paulo) `[S24]`.

### 7. Auto-pause (0 ACU) do Aurora Serverless v2 em sa-east-1

- O recurso é "uma capacidade mínima de 0 ACU"; pausa depois de um intervalo sem conexões iniciadas por usuário (mínimo 300 s, que é o padrão; máximo 86.400 s) e retoma quando chega uma conexão `[S22]`.
- Requisitos de versão: Aurora PostgreSQL 16.3, 15.7, 14.12 ou 13.15 (ou posteriores); Aurora MySQL 3.08.0 ou superior. Não se liga o auto-pause em versão sem suporte `[S22]`.
- Região: a página do auto-pause remete à página "Regiões e motores com suporte a Aurora serverless" para a lista de versões e regiões `[S22]`. Essa página lista **South America (São Paulo)** para Aurora PostgreSQL 18 (18.3+), 17 (17.4+), 16 (16.1+), 15 (15.2+), 14 (14.3+) e 13 (13.6+), e para Aurora MySQL (3.02.0+ e 8.4) `[S23]`. As versões mínimas do auto-pause `[S22]` são mais altas que as dessa tabela para PG 13 a 16.
- Não encontrado na fonte oficial: uma lista de regiões **específica do auto-pause** ou uma frase dizendo que algum recurso do auto-pause não existe em sa-east-1. `[inferência]` Como a documentação vincula o auto-pause à **versão do motor** `[S22]` e a lista de regiões é a do Serverless v2 `[S23]`, sa-east-1 deve suportá-lo com PG 17.4+/18.3+ (ou 16.3+, 15.7+, 14.12+, 13.15+); isso não está escrito com todas as letras e conviria confirmar criando um cluster de teste.
- **Tempo de retomada:** "tipicamente cerca de 15 segundos"; a AWS recomenda timeouts de cliente maiores que 15 s (por exemplo `connectTimeout` e `sslResponseTimeout` no JDBC). Se ficar pausada mais de 24 horas, a instância pode ir para um "sono mais profundo" e levar **30 segundos ou mais**, "aproximadamente como reiniciar a instância"; com inatividade acima de um dia, recomendam timeouts de 30 s ou mais `[S22]`.
- Cobrança pausada: instância e métrica `ServerlessV2Usage` ficam em zero; armazenamento e outros itens do cluster continuam cobrados `[S22]`. O status continua "Available" enquanto pausada `[S22]`.
- Quando **não** pausa: conexões de usuário abertas, patching/upgrade em andamento, **RDS Proxy** associado (mantém conexão aberta), cluster primário de banco global, replicação lógica ligada (PG) para o writer e leitores com prioridade 0 ou 1, e mínimo de capacidade acima de zero `[S22]`. Isso importa para o desenho: usar Data API ou conexão direta, sem RDS Proxy.
- Preço por ACU-hora em sa-east-1 vs us-east-1: não coberto aqui (já está em `banco-de-dados-aws.md`).

---

## Impacto nos tickets 08 e 09

| # | Resultado | Ticket 08 (plataforma) | Ticket 09 (banco/região) |
|---|---|---|---|
| 1 | iOS 26 permite desligar "Abrir como App Web"; isenção do ITP só está documentada para app web da Tela de Início; efeito do bookmark não está escrito (leitura nossa: perde a isenção) `[S1][S2]` | **Pesa contra PWA como única cópia dos dados.** A opção vem ligada por padrão, mas um toque a desliga. Mitiga: tratar o servidor (banco) como fonte de verdade e o armazenamento local do navegador como cache descartável; instruir os 2 usuários a manter "Open as Web App" ligado. Não elimina PWA. | Reforça manter os dados no banco (nuvem), não em IndexedDB/SQLite-WASM local. |
| 2 | ITP está ligado por padrão em todo WKWebView; App-Bound Domains não o desliga; Capacitor avisa que localStorage/IndexedDB podem ser perdidos `[S3][S4][S6]` | **Capacitor não resolve sozinho o risco de perda de dados do web view.** Dados que importam precisam de armazenamento nativo (Preferences/plugin SQLite) ou do servidor. Tira a vantagem "Capacitor = armazenamento durável" de PWA vs Capacitor. | Nenhuma mudança direta. |
| 3 | Expo: EAS na nuvem exige conta paga; release local no Xcode com conta gratuita é plausível, mas não documentado; profile de 7 dias `[S7][S8][S11][S12]` | **Expo/Capacitor com conta Apple gratuita implica reinstalar a cada 7 dias e ter um Mac com Xcode** (3 aparelhos permitidos). Isso pesa contra Expo/Capacitor no iPhone sem pagar US$ 99/ano; PWA não tem esse custo. Android não é afetado por isso. | Nenhuma mudança. |
| 4 | Android: verificação já vale no Brasil desde 2026-09-30 para lojas participantes; sideload direto "ainda não" segundo o FAQ, mas a página de conta limitada diz o contrário de forma geral; conta limitada grátis até 20 aparelhos `[S15][S16][S17]` | **Muda pouco, mas obriga a decidir:** APK direto no Android fica viável com conta limitada gratuita (registro de pacote, sem ID) ou com fluxo avançado; reconferir `[S15]`/`[S17]` antes de fechar. PWA no Android não passa por esse processo (a fonte não trata de PWA). Não derruba nenhuma das três opções. | Nenhuma mudança. |
| 5 | DSQL: tempo de retomada em segundos **não documentado**; só "mais lenta" `[S18]` | Sem efeito direto. | **Não é possível decidir DSQL vs Aurora Serverless v2 pelo tempo de retomada com base em doc oficial.** Itens para o protótipo: medir a primeira conexão de um cluster Idle/Inactive e definir timeouts e retentativas no cliente. Para 2 usuários com uso esporádico, a retomada será frequente. |
| 6 | DSQL: sem PITR documentado; só backup completo via AWS Backup (restaura em cluster novo) `[S19][S20][S21]` | Sem efeito. | **Pesa contra DSQL** se o requisito é restaurar a um instante antes de um erro (Aurora Serverless v2 tem PITR `[S20]`). DynamoDB com PITR já foi coberto em `banco-de-dados-aws.md`. Backup do DSQL exige cluster Active `[S18]`, o que atrapalha agendamento em cluster parado. |
| 7 | Auto-pause 0 ACU: documentado por versão de motor; sa-east-1 tem Serverless v2 nas versões listadas; retomada ≈ 15 s (30 s ou mais após 24 h); RDS Proxy impede a pausa `[S22][S23]` | Sem efeito. | **Não impede escolher sa-east-1 para Aurora Serverless v2**, com a ressalva de que a página não lista o auto-pause por região (confirmar com um cluster de teste). A retomada de 15 a 30 s ou mais pesa contra Aurora com pausa para um app usado de vez em quando; o custo de pausa vs mínimo 0,5 ACU fica como decisão do dono. |

Resumo para decisão: nada do que foi achado derruba uma opção sozinho. Em 08, os itens 1 e 2 enfraquecem a ideia de guardar dados só no aparelho (nos três caminhos) e o item 3 encarece Expo/Capacitor no iPhone. Em 09, o item 6 enfraquece o DSQL (sem PITR) e os itens 5 e 7 deixam as latências de retomada para medir num protótipo.

---

## Fontes

Todas acessadas em 2026-10-24.

- `[S1]` WebKit, "WebKit Features in Safari 26.0", 2025-09-15, seção "Every site can be a web app on iOS and iPadOS". https://webkit.org/blog/17333/webkit-features-in-safari-26-0/
- `[S2]` WebKit, "Tracking Prevention in WebKit" (sem data na página), seções ITP e "Home Screen Web Application Domain Exempt From ITP". https://webkit.org/tracking-prevention/
- `[S3]` WebKit, "App-Bound Domains", 2020-06-26, incluindo a seção "Intelligent Tracking Prevention in WKWebView". https://webkit.org/blog/10882/app-bound-domains/
- `[S4]` Apple, `WKWebViewConfiguration.limitsNavigationsToAppBoundDomains` (lido pelo JSON público da página). https://developer.apple.com/documentation/webkit/wkwebviewconfiguration/limitsnavigationstoappbounddomains
- `[S5]` Apple, `WKWebsiteDataStore` (lido pelo JSON público da página). https://developer.apple.com/documentation/webkit/wkwebsitedatastore
- `[S6]` Capacitor, "Storage" (docs v8). https://capacitorjs.com/docs/guides/storage
- `[S7]` Apple, Account Help, "About your developer account" (seção "Enable a personal team in Xcode"; sem data). https://developer.apple.com/help/account/basics/about-your-developer-account
- `[S8]` Expo, "Expo CLI" (`npx expo run:ios --configuration Release`, "iOS development signing"; sem data). https://docs.expo.dev/more/expo-cli/
- `[S9]` Expo, "Local app development". https://docs.expo.dev/guides/local-app-development/
- `[S10]` Expo, "Create a development build". https://docs.expo.dev/develop/development-builds/create-a-build/
- `[S11]` Expo, "Set up EAS Build". https://docs.expo.dev/build/setup/
- `[S12]` Expo, "Internal distribution". https://docs.expo.dev/build/internal-distribution/
- `[S13]` Expo, "Create a release build locally". https://docs.expo.dev/guides/local-app-production/
- `[S14]` Android Developers, "Android developer verification" (visão geral; sem data). https://developer.android.com/developer-verification
- `[S15]` Android Developers, "Frequently asked questions" da verificação (itens datados de 2025-09 a 2026-09-30; página atualizada em 2026-09-30). https://developer.android.com/developer-verification/guides/faq
- `[S16]` Android Developers, guia da verificação (atualizada em 2026-08-18). https://developer.android.com/developer-verification/guides
- `[S17]` Android Developers, "Register for limited distribution on Android devices" (atualizada em 2026-10-23). https://developer.android.com/developer-verification/guides/limited-distribution
- `[S18]` AWS, "Aurora DSQL cluster lifecycle". https://docs.aws.amazon.com/aurora-dsql/latest/userguide/cluster-lifecycle.html
- `[S19]` AWS, "Backup and restore for Amazon Aurora DSQL". https://docs.aws.amazon.com/aurora-dsql/latest/userguide/backup-aurora-dsql.html
- `[S20]` AWS, "AWS Backup feature availability" (tabelas por recurso e por região). https://docs.aws.amazon.com/aws-backup/latest/devguide/backup-feature-availability.html
- `[S21]` AWS, "Continuous backups and point-in-time recovery (PITR)" do AWS Backup. https://docs.aws.amazon.com/aws-backup/latest/devguide/point-in-time-recovery.html
- `[S22]` AWS, "Scaling to Zero ACUs with automatic pause and resume for Aurora serverless". https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html
- `[S23]` AWS, "Supported Regions and Aurora DB engines for Aurora serverless". https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.Aurora_Fea_Regions_DB-eng.Feature.ServerlessV2.html
- `[S24]` AWS, "What is Amazon Aurora DSQL?" (tabela de endpoints, inclui sa-east-1). https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html
- `[S25]` AWS Database Blog, "Amazon Aurora DSQL connections: Drivers, strings, and best practices" (consultado; sem número de retomada). https://aws.amazon.com/blogs/database/amazon-aurora-dsql-connections-drivers-strings-and-best-practices/
- `[S26]` AWS Database Blog, "Connection pooling strategies in Amazon Aurora DSQL" (consultado; sem número de retomada). https://aws.amazon.com/blogs/database/connection-pooling-strategies-in-amazon-aurora-dsql/

## Lacunas remanescentes

- Efeito explícito de "Open as Web App" desligado sobre o ITP (só `[inferência]`).
- ITP de 7 dias sobre conteúdo local em WKWebView de app Capacitor (fonte não diz).
- Release com conta Apple gratuita pelo Expo (não documentado; só dev build).
- Divergência de alcance do sideload no Brasil entre `[S15]` e `[S17]`.
- Segundos de retomada do DSQL; tempos até Idle e Inactive; agendamento de backup em cluster parado.
- Lista de regiões específica do auto-pause do Aurora Serverless v2.
