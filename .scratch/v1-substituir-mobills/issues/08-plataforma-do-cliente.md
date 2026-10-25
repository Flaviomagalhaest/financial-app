# Plataforma do cliente

Type: grilling
Status: resolved
Blocked by: 02
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Issue: #26
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Com o que o app chega à web, ao Android e ao iPhone?

- app web instalável (PWA);
- Expo (React Native com saída web), que o dono já usa em outro repositório;
- app web empacotado com Capacitor.

Pesar: loja de apps não é requisito; funcionar sem internet e ter atalho na tela inicial são; gráficos e dashboards; custo (Apple Developer); manutenção por uma pessoa; uma só base de código para os três. Usar o achado de [Limites do app web instalável no iPhone e no Android](02-limites-do-app-web-instalavel.md).

## Checklist

- [x] Decisão registrada em `## Answer`
- [x] ADR em `docs/adr/` se a decisão for difícil de reverter, surpreendente e fruto de um trade-off real

## Answer

O app é um **app web instalável (PWA)** em **React + TypeScript**, uma só base de código para a web do computador (layout para tela larga), o Android e o iPhone. Sem loja de apps, sem Apple Developer (US$ 99/ano) e sem Mac. [ADR 0005](../../../docs/adr/0005-app-web-instalavel-em-vez-de-app-nativo.md).

- **iPhone (iOS atualizado):** instala por Compartilhar > Adicionar à Tela de Início, o que o isenta do apagamento de 7 dias. O ícone abre o app normalmente: **no iPhone não há atalho** para o novo lançamento. Lançamento feito sem internet só sobe com o app aberto (não há Background Sync).
- **Android (Chrome com Google Play):** instala como WebAPK; o toque longo no ícone mostra o atalho **"Novo lançamento"** (`shortcuts` do manifesto). A sincronização pode rodar em segundo plano.
- **Computador:** a mesma PWA no navegador, instalável no Chrome e no Edge se quiserem.
- **Fila offline:** o app mostra quantos lançamentos aguardam envio; como a fila e os conflitos funcionam fica para "Sincronização offline e conflitos" no mapa.
- **Plano B:** se a PWA decepcionar no uso real, o mesmo app web é empacotado com Capacitor.
- **Validação:** sem protótipo antes desta decisão; a primeira etapa da spec instala o app nos dois celulares e testa o offline.
- **Fora daqui:** ferramentas de build e bibliotecas de gráfico ficam para a spec e o [ticket 11](11-dashboards-e-fechamento-do-mes.md); a rapidez de lançar no iPhone sem atalho, para o [ticket 10](10-fluxo-de-lancamento-rapido.md).

Por que não Expo nem Capacitor agora: no iPhone, fora da loja, eles exigem Mac e reinstalação a cada 7 dias, ou US$ 99/ano (uns US$ 8 por mês, acima do teto de US$ 5). A saída web do Expo herdaria os limites da PWA. Gráficos e dashboards têm bibliotecas mais maduras na web.

Efeito no [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md): saem o build de release do Expo com conta gratuita e o alcance do sideload de APK no Brasil, que só pesavam num app nativo; ficam o "Abrir como App Web" do iOS 26 e o ITP no WKWebView, que importa para o plano B.
