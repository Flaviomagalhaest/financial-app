# Limites do app web instalável (PWA) no iPhone e no Android, e custo dos caminhos alternativos

Origem: [ticket 02](../issues/02-limites-do-app-web-instalavel.md) do [mapa V1](../map.md). Decisão que espera por isto: Plataforma do cliente (ticket 08).

Data de acesso de todas as fontes: **2026-10-24**. Só fontes primárias (WebKit, MDN, web.dev, Apple Developer, Android Developers, SQLite, Expo, Capacitor). Onde a fonte oficial não diz, está escrito "não encontrado na fonte oficial". Itens marcados **[inferência]** são conclusão minha a partir das fontes, não afirmação delas. Cada afirmação traz o código da fonte `[Sx]`, listada no fim com URL e data de publicação/atualização da página quando ela informa.

Versões: "iOS 17" etc. refere-se ao iOS/iPadOS e ao Safari de mesmo número (WebKit numera igual). "Chrome Android" refere-se ao Chrome para Android. Dados de suporte por versão vêm do `@mdn/browser-compat-data` 8.1.7 (publicado em 2026-10-22) `[S11]`.

---

## 1. Resumo (um item do "Levantar" por vez)

### App web instalável

**1.1 Instalação, ícone e tela cheia: sim nos dois, com um jeito diferente em cada.**
- iPhone: não existe aviso de instalação; o usuário usa Compartilhar > Adicionar à Tela de Início `[S12]`. Desde o iOS 16.4 isso também funciona a partir de Chrome, Edge, Firefox e Orion `[S4][S14]`. **No iOS 26 qualquer site adicionado abre como app web por padrão** (o usuário pode desligar "Abrir como App Web"), sem exigir manifesto `[S15]`. Antes do iOS 26 era preciso manifesto com `display: standalone|fullscreen` ou a meta tag `apple-mobile-web-app-capable` `[S14]`. No iOS só existe o modo `standalone` (`fullscreen` cai para `standalone`, `minimal-ui` vira atalho de navegador) `[S12]`. Ícone: `apple-touch-icon` tem prioridade sobre o ícone do manifesto; ícones no manifesto valem desde o iOS 15.4 `[S14][S11]`.
- Android: no Chrome com Google Mobile Services o PWA vira WebAPK (ícone no lançador, aparece em Configurações > Apps); em Firefox, Edge, Opera e Chrome sem GMS vira só atalho com selo do navegador `[S4][S12]`. Critérios do Chrome: HTTPS, `name`/`short_name`, ícones 192 px e 512 px, `start_url`, `display`, e `prefer_related_applications` falso `[S4]`. Há `beforeinstallprompt` (botão "Instalar" próprio) no Chrome Android; no Safari iOS não `[S4][S11]`.

**1.2 Sem internet e quanto cabe: dá, e o espaço não é o problema; a persistência é.**
- Service worker: Safari iOS desde 11.3, Chrome Android desde 40. IndexedDB: Safari iOS desde 8. OPFS e `FileSystemSyncAccessHandle`: Safari iOS desde 15.2, Chrome Android desde 109 `[S11]`.
- Cota por origem: iOS 17 em diante, app web da Tela de Início tem a mesma cota do Safari, **até ~60% do disco por origem** (cota total de todas as origens: 80%); antes do iOS 17 era 1 GiB com pedido de permissão `[S1][S3]`. Chrome Android: até 60% do disco por origem `[S3]`. Faltando espaço, a gravação falha com `QuotaExceededError` `[S1][S3]`.
- SQLite em WASM: o projeto SQLite oferece VFS em OPFS. O `opfs-sahpool` funciona nos navegadores principais lançados desde março de 2023 e **não exige** os cabeçalhos COOP/COEP; o VFS `opfs` exige COOP/COEP (por causa de `SharedArrayBuffer`) e Safari 17 ou mais novo `[S17]`. O `opfs-sahpool` não aceita várias conexões simultâneas ao mesmo banco (limitação relevante para várias abas) `[S17]`. O SQLite avisa que bancos em OPFS às vezes "somem" por decisão do navegador, antivírus ou limpadores `[S17]`.
- **Background Sync (`SyncManager`) não existe no Safari iOS** (Chrome Android desde 49), e Periodic Background Sync também não `[S11][S10]`. **[inferência]** A fila de lançamentos feitos offline só pode ser enviada com o app aberto no iPhone.

**1.3 O iOS apaga dados de app web parado? Sim para site no Safari; o app instalado na Tela de Início é isento da regra dos 7 dias.**
- Regra do Safari: ITP apaga **todo armazenamento gravável por script** (IndexedDB, localStorage, registros e cache de service worker, sessionStorage, cookies criados por JS) após **7 dias de uso do navegador sem interação do usuário com o site** `[S2][S3]`. Cookies definidos pelo servidor (`Set-Cookie`) ficam de fora dessa limpeza `[S3]`.
- **Instalar na Tela de Início muda isso:** o domínio de um app web da Tela de Início é isento do limite de 7 dias, e seus dados ficam isolados do Safari `[S2]`.
- Continua valendo a limpeza por falta de espaço e por exceder a cota total: ordem do menos recentemente usado, por origem inteira (tudo ou nada); origens em modo persistente (`navigator.storage.persist()`) ficam de fora `[S1][S3]`. O WebKit concede `persist()` por heurística, citando como exemplo ser um app web da Tela de Início `[S1]`.
- **[inferência]** No iOS 26, se o usuário desligar "Abrir como App Web" ao adicionar, vira favorito do navegador e a isenção deixaria de se aplicar; não encontrado na fonte oficial um texto que diga isso explicitamente.
- Não encontrado na fonte oficial: o que acontece com dados de um app instalado que fica meses sem abrir, além da regra de menos recentemente usado sob pouco espaço.
- Chrome Android: a remoção proativa por inatividade "acontece só no Safari"; no Chrome só há remoção sob falta de espaço, e a equipe do Chrome diz que é muito rara para quem visita com regularidade `[S3]`. A instalação do PWA é um dos critérios do Chrome para conceder `persist()` `[S13]` (página de 2022).
- Cada instalação do mesmo app no iOS tem armazenamento isolado `[S12][S14]`.
- **[inferência]** Por tudo isso o servidor deve ser a fonte da verdade e o aparelho guarda cache e fila de envio.

**1.4 Atalhos no ícone: Android sim, iPhone não.**
- `shortcuts` do manifesto: Chrome Android desde 84; **Safari iOS: não suportado** (Safari no macOS desde 17.4) `[S11]`. A web.dev (2024) também diz que PWAs no iOS não têm app shortcuts `[S12]`. No Android funcionam em WebAPK; em atalho simples (sem WebAPK) não `[S12]`. O sistema pode truncar a lista `[S5]`.
- Um atalho "Novo lançamento" (ex.: `url: "/lancamentos/novo"`) funcionaria no Android com WebAPK. No iPhone, a alternativa documentada é fazer o `start_url` do app abrir direto na tela de novo lançamento (`start_url` é suportado no iOS) `[S11]`. Não encontrado na fonte oficial outra forma de ter atalho de ícone no iOS para app web (nada sobre o app Atalhos da Apple nas fontes consultadas).

**1.5 Login que dura entre aberturas: possível; no iOS o app instalado começa deslogado.**
- Cookie persistente definido pelo servidor (`Max-Age`/`Expires`) sobrevive ao fechamento do app `[S25]`, e não entra na limpeza proativa de 7 dias do Safari `[S3]`. Cookies criados por JavaScript entram nos 7 dias, a menos que o app esteja instalado `[S2]`.
- Os dados do app da Tela de Início ficam isolados do Safari `[S2]`, então **a sessão aberta no Safari não vale no ícone**; é preciso entrar de novo dentro do app instalado. (A cópia automática de cookies do Safari para o app existe só no "Adicionar ao Dock" do macOS Sonoma, segundo o WebKit `[S16]`; para iOS não encontrado na fonte oficial.)
- Não encontrado na fonte oficial: teto de validade de cookie imposto pelo Safari iOS a cookie de servidor em app da Tela de Início; comportamento de cookies entre Chrome e WebAPK no Android; passkeys em app web instalado (não pesquisado).

### Caminhos alternativos

**1.6 Expo (React Native com saída web).**
- A saída web (`npx expo export --platform web`) existe, mas o próprio Expo recomenda app nativo para melhor offline e diz que service worker "pode causar comportamento inesperado"; PWA no Expo é manifesto + Workbox, manual `[E7][E8]`. Para SQLite na web o Expo usa WASM e exige COOP/COEP e configuração do Metro `[E9]`. Ou seja, o lado web do Expo herda todos os limites do item 1.2 a 1.5.
- **iPhone sem loja e sem pagar:** só por build local com Xcode em um Mac (`npx expo run:ios --device`; Developer Mode ligado; bundle id único). O Expo diz ser "a única forma" de instalar um development build sem conta Apple paga `[E1]`. Pelas regras da Apple de conta gratuita ("Personal Team") o perfil **expira em 7 dias** e é preciso recompilar e reinstalar; limite de 3 dispositivos e 3 apps por dispositivo `[S18]`. Não encontrado na fonte do Expo: detalhe de build de release (não development) com conta gratuita.
- **iPhone sem loja, pagando:** Apple Developer Program **US$ 99 por ano** `[S19][S20]`. Com ele o EAS Build faz distribuição interna "ad hoc": registra o UDID de cada aparelho (`eas device:create`), gera perfil só para eles; no máximo **100 iPhones por ano**; novo aparelho exige novo build ou reassinatura; em conta nova a Apple pode levar 24 a 72 h para processar o aparelho `[E2]`. Instalação por URL/QR do EAS `[E2]`.
- **iPhone com loja (TestFlight):** exige conta paga `[E4]`. `eas submit` envia a build; ela aparece no TestFlight após processamento (normalmente 10 a 15 min) `[E4]`. TestFlight: build testável por até **90 dias** (depois fica indisponível); até 100 testadores internos (usuários do App Store Connect) e 10.000 externos; a primeira build para externos passa por revisão da Apple `[S22]`. **[inferência]** Para o casal, seria preciso renovar a build ao menos a cada 90 dias e dar à esposa acesso interno ao App Store Connect (ou usar convite externo com revisão).
- **Android com APK direto:** perfil EAS com `distribution: "internal"` ou `android.buildType: "apk"` gera `.apk`; instala-se baixando pelo URL no celular ou por `adb install`, aceitando o aviso de app fora da Play Store `[E2][E3]`. AAB só serve para a Play Store `[E2]`. Também dá para compilar localmente com Android Studio `[E1]`.
- **Custo do EAS:** plano Free: 15 builds Android + 15 iOS por mês, fila de baixa prioridade, timeout de 45 min; planos pagos a partir de US$ 19/mês `[E5][E6]`.

**1.7 Capacitor (app web empacotado).**
- O Capacitor 8 embrulha o build web em WKWebView (iOS 15+, Xcode 26.0+ obrigatório, logo precisa de Mac) e no Android System WebView (API 24+, Android Studio 2025.2.1+) `[C1][C2][C3]`. Fluxo: build web, `npx cap sync`, `npx cap run ios|android`; `npx cap build android` gera AAB/APK assinado `[C4]`.
- **iPhone sem loja e com loja:** o Capacitor diz que o app é um app nativo comum e vai à App Store como qualquer outro `[C6]`. As regras de assinatura são as da Apple, portanto as mesmas do Expo: conta gratuita com perfil de 7 dias `[S18]`; US$ 99/ano para ad hoc (100 aparelhos/ano `[E2]`) ou TestFlight (90 dias por build) `[S20][S22]`. O Capacitor não tem serviço próprio de build/distribuição na documentação consultada (menciona o Appflow da Ionic; não verifiquei preço nem disponibilidade atual).
- **Android:** APK/AAB assinado gerado pelo Android Studio ou `cap build` `[C4]`; instalação direta de APK vale a mesma ressalva da verificação de desenvolvedores do Android (item 3.3).
- **Armazenamento:** o Capacitor avisa que localStorage e, no iOS, IndexedDB "devem ser considerados transitórios" porque o sistema pode recuperar espaço de WebViews com pouco espaço; recomenda a API nativa `Preferences` (só para pouco dado) e SQLite via plugin da comunidade para volume `[C5]`. O WebKit dá a apps que não são navegador (como o WKWebView do Capacitor) cota por origem menor, ~15% do disco (total 20%) `[S1][S3]`. Não encontrado na fonte oficial: se o limite de 7 dias do ITP vale dentro do WKWebView de um app Capacitor.

---

## 2. Comparativo em uma tabela

| Aspecto | PWA iPhone (iOS 16.4 a 26) | PWA Android (Chrome, GMS) | Expo / Capacitor no iPhone | Expo / Capacitor no Android |
|---|---|---|---|---|
| Instalar | Compartilhar > Adicionar à Tela de Início; iOS 26 abre como app por padrão `[S12][S15]` | Aviso do Chrome, vira WebAPK `[S4][S12]` | Mac + Xcode; conta grátis (perfil 7 dias) ou US$ 99/ano `[S18][S20]` | APK direto ou Play Store `[E2][E3]` |
| Atalho no ícone | Não `[S11][S12]` | Sim, `shortcuts` (Chrome 84+) `[S11]` | Não encontrado na fonte oficial | Não encontrado na fonte oficial |
| Offline | SW + IndexedDB/OPFS; sem Background Sync `[S11]` | SW + IndexedDB/OPFS + Background Sync `[S11]` | Armazenamento nativo/SQLite `[C5]` | idem |
| Risco de perder dados | Isento dos 7 dias se instalado; ainda sujeito a falta de espaço `[S2][S1]` | Só sob falta de espaço, raro `[S3]` | IndexedDB do WebView pode ser recuperado; usar SQLite nativo `[C5]` | idem |
| Custo | US$ 0 | US$ 0 | US$ 0 (7 dias) ou US$ 99/ano `[S18][S20]` | US$ 0 (APK); US$ 25 só se for registrar no Android Developer Console (ver 3.3) `[A2]` |

---

## 3. Detalhes e ressalvas

### 3.1 O que a Apple mudou e a documentação antiga ainda diz
- A web.dev (atualizada em 2024-09-20) diz que PWAs no iOS não têm suporte a "badging" `[S12]`, mas o WebKit lançou a Badging API para apps da Tela de Início no iOS 16.4 (2023-02-16) `[S14]`, e a tabela do MDN confirma Safari iOS 16.4 `[S11]`. Vale a fonte do WebKit.
- A mesma página diz que "Safari para macOS não suporta instalação"; o MDN (2026-10-06) e o WebKit (Safari 17) dizem o contrário (Adicionar ao Dock) `[S4][S16]`. Irrelevante para este projeto, mas mostra que a web.dev está defasada em pontos; por isso preferi WebKit/MDN onde divergem.
- `StorageManager.persist()`: o MDN/BCD marca Safari desde 15.2, enquanto o WebKit diz que a Storage API ficou "totalmente suportada" no Safari 17 e que `estimate()` é 17 `[S1][S11]`. Para decisão de produto, tratar como "confiável a partir do iOS 17".

### 3.2 Regra dos 7 dias, em detalhe
- A página de prevenção de rastreamento do WebKit não traz data de publicação `[S2]`; o texto vale como "comportamento em produção" na data de acesso.
- MDN descreve a mesma regra como "7 dias de **uso do navegador** sem clique ou toque" e só com a proteção de rastreamento entre sites ligada `[S3]`. O WebKit fala em "7 dias sem interação do usuário com o site" `[S2]`. Não encontrado na fonte oficial: se o contador do app instalado conta tempo de calendário.
- Existe também uma regra separada de 30 dias que apaga todos os dados de domínios classificados como rastreadores `[S2]`; não se aplica a um site próprio de finanças.

### 3.3 Verificação de desenvolvedores do Android (afeta "APK direto")
- O Google passou a exigir que apps sejam registrados por desenvolvedores verificados para instalar em dispositivos Android certificados. **Efetivo em 30 de setembro de 2026 em Brasil, Indonésia, Singapura e Tailândia**, apenas para instalações vindas de lojas participantes (Google Play, Honor, OPPO, Samsung Galaxy Store, Transsion, vivo, Xiaomi), e expansão global em 2027 `[A1][A3]`.
- Segundo o FAQ (itens atualizados em 2026-07-15), quem instala APK baixado direto (sideload) ou usa loja fora da lista **ainda não é afetado**, mas o Google recomenda se registrar antes de 2027 `[A2]`. A página da conta de distribuição limitada diz que pacotes não registrados "não serão mais instaláveis" nessas regiões `[A4]`; as duas páginas parecem divergir no alcance, então **a regra precisa ser reconferida antes de decidir por APK direto**.
- Instalar via `adb` está dispensado de verificação `[A2]`. Usuários avançados terão um "fluxo avançado" único para instalar apps de desenvolvedores não verificados (lançado em agosto de 2026) `[A2]`.
- Para um app de uso pessoal: conta de **distribuição limitada** é gratuita, sem documento de identidade, até **20 aparelhos** autorizados por QR code ou link `[A4]`; conta de distribuição plena custa US$ 25 `[A2]`.
- Se o casal está no Brasil, a região já entra na lista de aplicação. Esta pesquisa não verificou onde o casal mora; o repositório está em português do Brasil.

### 3.4 Apple: custos e prazos citados
- Apple Developer Program: US$ 99 por ano (moeda local onde houver) `[S19][S20]`. Inscrição de pessoa física exige Apple Account com autenticação em dois fatores e maioridade legal `[S20]`.
- Conta gratuita ("Personal Team"): até 10 App IDs, 3 dispositivos e 3 apps por dispositivo; perfis e IDs expiram em 7 dias; é preciso recompilar e reinstalar `[S18]`. A página da Apple não traz data.
- O Xcode documenta que para rodar em aparelho físico basta entrar com Apple Account do programa **ou pessoal** em Xcode > Settings > Apple Accounts e ativar "Automatically manage signing" `[S23]`.
- Distribuição por aparelhos registrados é "limitada por família de produto por ano" `[S24]`; o Expo concretiza em 100 iPhones por ano e diz que aparelhos desativados continuam contando `[E2]`.
- Alternativas fora da App Store (UE etc.) existem "em certas regiões" `[S19]`; não pesquisei condições.

### 3.5 O que cada caminho exige de máquina
- PWA: nada além de hospedagem HTTPS (a AWS já prevista no mapa).
- Expo: EAS compila na nuvem sem Mac e envia à App Store de qualquer SO `[E1][E4]`; build local de iOS pede Mac com Xcode `[E1]`.
- Capacitor: build de iOS exige Mac com Xcode 26.0+; Android exige Android Studio 2025.2.1+ `[C3]`.

---

## 4. Lacunas (não encontrado na fonte oficial ou não pesquisado)

1. Se um app da Tela de Início sem uso por meses perde dados fora da regra de menos recentemente usado sob falta de espaço, e o efeito de desligar "Abrir como App Web" no iOS 26 sobre a isenção do ITP.
2. Teto de validade de cookie de servidor no Safari iOS; compartilhamento de cookies entre Chrome e WebAPK; passkeys e preenchimento automático em app web instalado.
3. Qualquer forma de atalho de ícone para app web no iOS (a única documentada é `start_url`); atalhos de ícone em Expo e Capacitor (exigiriam código nativo; a documentação consultada não os cobre).
4. Se o ITP de 7 dias vale dentro do WKWebView de um app Capacitor.
5. Expo: build de release (não development) com conta Apple gratuita.
6. Capacitor: preço e situação atual do Appflow (apenas citado pela documentação).
7. Alcance real da verificação de desenvolvedores do Android sobre APK baixado direto no Brasil (FAQ e página de conta limitada divergem) e se o casal está no Brasil.
8. Preços e prazos de páginas sem data (Expo pricing, Apple Developer Account Help, WebKit Tracking Prevention) refletem a data de acesso; reconferir antes de gastar.
9. Desempenho e experiência real (animações, teclado, tempo de abertura a frio) do PWA no iPhone: não coberto por fontes oficiais; seria assunto para o protótipo.

---

## 5. Fontes

Todas acessadas em 2026-10-24.

**WebKit / Apple**
- `[S1]` WebKit, "Updates to Storage Policy", 2023-08-10. https://webkit.org/blog/14403/updates-to-storage-policy/
- `[S2]` WebKit, "Tracking Prevention in WebKit" (sem data na página). https://webkit.org/tracking-prevention/
- `[S14]` WebKit, "Web Push for Web Apps on iOS and iPadOS", 2023-02-16. https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/
- `[S15]` WebKit, "WebKit Features in Safari 26.0", 2025-09-15. https://webkit.org/blog/17333/webkit-features-in-safari-26-0/
- `[S16]` WebKit, "WebKit Features in Safari 17.0", 2023-09-18. https://webkit.org/blog/14445/webkit-features-in-safari-17-0/
- `[S18]` Apple, Account Help, "About your developer account" (sem data; endereço final de `developer.apple.com/support/compare-memberships/`). https://developer.apple.com/help/account/basics/about-your-developer-account
- `[S19]` Apple, "Membership Details". https://developer.apple.com/programs/whats-included/
- `[S20]` Apple, "Become a member" (inscrição e preço). https://developer.apple.com/programs/enroll/
- `[S22]` Apple, "TestFlight overview". https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview
- `[S23]` Apple, "Running your app on simulated or physical devices" (documentação do Xcode, lida pelo JSON público da página). https://developer.apple.com/documentation/xcode/running-your-app-on-simulated-or-physical-devices
- `[S24]` Apple, "Distributing your app to registered devices". https://developer.apple.com/documentation/xcode/distributing-your-app-to-registered-devices

**MDN / web.dev / SQLite**
- `[S3]` MDN, "Storage quotas and eviction criteria", última edição 2026-01-05. https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria
- `[S4]` MDN, "Making PWAs installable", 2026-10-06. https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable
- `[S5]` MDN, manifesto `shortcuts`, 2025-11-30. https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/shortcuts
- `[S6]` MDN, manifesto `display`, 2025-08-08. https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/display
- `[S7]` MDN, "Origin private file system", 2025-07-14. https://developer.mozilla.org/en-US/docs/Web/API/File_System_API/Origin_private_file_system
- `[S8]` MDN, `StorageManager.persist()`, 2026-10-12. https://developer.mozilla.org/en-US/docs/Web/API/StorageManager/persist
- `[S9]` MDN, "Service Worker API", 2026-08-15. https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API
- `[S10]` MDN, "Background Synchronization API", 2024-04-22. https://developer.mozilla.org/en-US/docs/Web/API/Background_Synchronization_API
- `[S11]` MDN browser-compat-data 8.1.7 (publicada em 2026-10-22), pacote npm `@mdn/browser-compat-data`, baixado de https://unpkg.com/@mdn/browser-compat-data@latest/data.json (chaves `manifests.webapp.shortcuts`, `.display`, `.icons`, `.id`, `api.SyncManager`, `api.PeriodicSyncManager`, `api.StorageManager.persist`, `.estimate`, `api.ServiceWorkerRegistration`, `api.IDBFactory`, `api.StorageManager.getDirectory`, `api.FileSystemSyncAccessHandle`, `api.Window.beforeinstallprompt_event`, `api.Navigator.setAppBadge`). Fonte primária é o repositório https://github.com/mdn/browser-compat-data; usei o pacote publicado.
- `[S12]` web.dev, "Installation", atualizada 2024-09-20. https://web.dev/learn/pwa/installation
- `[S13]` web.dev, "Offline data", atualizada 2022-01-10. https://web.dev/learn/pwa/offline-data
- `[S17]` SQLite, "Persistent Storage Options" (WASM; sem data). https://sqlite.org/wasm/doc/trunk/persistence.md
- `[S25]` MDN, "Set-Cookie" (`Max-Age`, `Expires`, cookies permanentes). https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie

**Expo**
- `[E1]` "Introduction to development builds". https://docs.expo.dev/develop/development-builds/introduction/
- `[E2]` "Internal distribution". https://docs.expo.dev/build/internal-distribution/
- `[E3]` "Build APKs for Android Emulators and devices". https://docs.expo.dev/build-reference/apk/
- `[E4]` "Submit to the Apple App Store with EAS Submit". https://docs.expo.dev/submit/ios/
- `[E5]` Preços do EAS (sem data). https://expo.dev/pricing
- `[E6]` "Subscriptions, plans, and add-ons". https://docs.expo.dev/billing/plans/
- `[E7]` "Progressive web apps". https://docs.expo.dev/guides/progressive-web-apps/
- `[E8]` "Develop websites with Expo". https://docs.expo.dev/workflow/web/
- `[E9]` "SQLite" (seção Web). https://docs.expo.dev/versions/latest/sdk/sqlite/

**Capacitor (documentação v8)**
- `[C1]` iOS. https://capacitorjs.com/docs/ios
- `[C2]` Android. https://capacitorjs.com/docs/android
- `[C3]` Environment setup. https://capacitorjs.com/docs/getting-started/environment-setup
- `[C4]` Development workflow. https://capacitorjs.com/docs/basics/workflow
- `[C5]` Storage. https://capacitorjs.com/docs/guides/storage
- `[C6]` Deploying to App Store. https://capacitorjs.com/docs/ios/deploying-to-app-store

**Android**
- `[A1]` "Android developer verification". https://developer.android.com/developer-verification
- `[A2]` FAQ da verificação (itens datados de 2025-09 a 2026-09-30). https://developer.android.com/developer-verification/guides/faq
- `[A3]` Guia da verificação. https://developer.android.com/developer-verification/guides
- `[A4]` "Register for limited distribution on Android devices". https://developer.android.com/developer-verification/guides/limited-distribution
