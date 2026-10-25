# Limites do app web instalável no iPhone e no Android

Type: research
Status: resolved
Blocked by: —
Skills: `research` (AFK, em sub-agente)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #20
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Em 2026, um app web instalável (PWA) aguenta o uso diário do casal no iPhone (Safari/iOS) e no Android (Chrome)? E quanto custam e o que exigem os caminhos alternativos?

Levantar, para o app web instalável:

- instalação na tela inicial, ícone e abertura em tela cheia;
- funcionamento sem internet (service worker) e quanto dá para guardar no aparelho (IndexedDB, OPFS, SQLite em WASM);
- se o iOS apaga os dados guardados de sites ou apps que ficam um tempo sem ser abertos, e se instalar na tela inicial muda isso;
- atalhos no ícone que abrem direto uma tela (ex.: novo lançamento);
- login que continua valendo entre aberturas do app.

Levantar, para os caminhos alternativos:

- Expo (React Native com saída web): o que é preciso para rodar no iPhone sem loja e com loja (Apple Developer US$ 99/ano, TestFlight, perfil gratuito que expira) e no Android (APK direto);
- Capacitor (app web empacotado): as mesmas perguntas.

Decisão que espera por isso: [Plataforma do cliente](08-plataforma-do-cliente.md).

## Checklist

- [x] Fontes primárias: WebKit (blog e docs), MDN, web.dev, documentação da Apple para desenvolvedores, documentação do Expo e do Capacitor
- [x] Achados num único Markdown, cada afirmação com a fonte, numa branch `research/app-web-instalavel` enviada e sem PR
- [x] Ponteiro para a branch e resumo do achado neste ticket, em `## Answer`

## Answer

Achados completos na branch `research/app-web-instalavel` (arquivo `.scratch/v1-substituir-mobills/research/app-web-instalavel.md`, commit `6e4854a`), enviada sem PR e sem tag. Fontes primárias (WebKit, MDN, web.dev, Apple, Android Developers, Expo, Capacitor), acessadas em 2026-10-24.

- **Instalação:** no iPhone é manual (Compartilhar > Adicionar à Tela de Início); no iOS 26 o site abre como app web por padrão. No Android, o Chrome com GMS instala como WebAPK.
- **Offline:** service worker, IndexedDB e OPFS funcionam nos dois; SQLite-WASM em OPFS (`opfs-sahpool`) funciona, sem várias conexões. **Não há Background Sync no Safari iOS:** a fila offline só sincroniza com o app aberto.
- **Apagamento no iOS:** o ITP apaga o armazenamento de sites após 7 dias sem interação; **o app instalado na Tela de Início é isento**. Falta de espaço ainda pode apagar, a menos que `persist()` seja concedido.
- **Atalhos no ícone:** `shortcuts` do manifesto funciona no Chrome Android, **não no Safari iOS**. No iPhone, a alternativa é apontar o `start_url` para a tela de novo lançamento.
- **Login:** cookie de servidor persistente sobrevive; no iOS o app instalado começa deslogado (storage isolado do Safari).
- **Expo:** a saída web herda os limites da PWA. iPhone sem pagar: só build local (Mac + Xcode) com perfil que **expira em 7 dias**. Com Apple Developer (US$ 99/ano): ad hoc pelo EAS ou TestFlight. Android: APK direto.
- **Capacitor v8:** exige Mac com Xcode 26+; mesmas regras da Apple; a documentação diz que IndexedDB no iOS é transitório e recomenda SQLite nativo.
- **Novidade:** a verificação de desenvolvedores do Android vale desde 30/09/2026 no Brasil para lojas participantes; sideload ainda não é afetado segundo o FAQ do Google, mas as páginas oficiais divergem.

Lacunas (detalhadas no arquivo da branch): efeito de desligar "Abrir como App Web" no iOS 26 sobre a isenção do ITP; se o ITP vale dentro do WKWebView do Capacitor; atalho de ícone no iOS por outro meio; build de release no Expo com conta Apple gratuita; alcance real da verificação do Android. Seguem em [Reconferir as lacunas das pesquisas de plataforma e de banco](15-reconferir-lacunas-das-pesquisas.md).
