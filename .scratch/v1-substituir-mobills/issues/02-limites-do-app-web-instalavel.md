# Limites do app web instalável no iPhone e no Android

Type: research
Status: open
Blocked by: 13
Skills: `research` (AFK, em sub-agente)
Modelo recomendado: Sonnet
Effort recomendado: medium
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

- [ ] Fontes primárias: WebKit (blog e docs), MDN, web.dev, documentação da Apple para desenvolvedores, documentação do Expo e do Capacitor
- [ ] Achados num único Markdown, cada afirmação com a fonte, numa branch `research/app-web-instalavel` enviada e sem PR
- [ ] Ponteiro para a branch e resumo do achado neste ticket, em `## Answer`
