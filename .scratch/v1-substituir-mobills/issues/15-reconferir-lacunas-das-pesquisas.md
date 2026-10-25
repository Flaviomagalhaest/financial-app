# Reconferir as lacunas das pesquisas de plataforma e de banco

Type: research
Status: resolved
Blocked by: —
Skills: `research` (AFK, em sub-agente); a parte da conta AWS é HITL (o dono confere no console da conta pagadora)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #33
Origem: lacunas de [Limites do app web instalável no iPhone e no Android](02-limites-do-app-web-instalavel.md) e [Banco de dados na AWS para dois usuários e histórico longo](03-banco-de-dados-na-aws.md)

## Question

Que pontos das duas pesquisas ficaram sem fonte oficial e ainda pesam em [Plataforma do cliente](08-plataforma-do-cliente.md) e [Banco de dados e região](09-banco-de-dados-e-regiao.md)?

## Checklist

- [x] Plataforma: efeito de desligar "Abrir como App Web" no iOS 26 sobre a isenção do ITP de 7 dias; se o ITP vale no WKWebView de um app Capacitor; build de release no Expo com conta Apple gratuita; alcance da verificação de desenvolvedores do Android sobre APK direto no Brasil (as páginas oficiais divergem)
- [x] Banco: tempo de retomada do DSQL em segundos; PITR no DSQL; auto-pause do Aurora Serverless v2 em sa-east-1
- [x] Conta AWS (HITL, movido para o ticket 16): prazo e origem dos US$ 120 de crédito, e se o compartilhamento de créditos está ligado na conta pagadora (a FAQ da AWS se contradiz sobre a validade)
- [x] Achados num único Markdown, cada afirmação com a fonte, numa branch `research/lacunas-plataforma-e-banco` enviada e sem PR
- [x] Ponteiro para a branch e resumo em `## Answer`; dizer se algo muda os tickets 08 ou 09

## Answer

Achados na branch `research/lacunas-plataforma-e-banco` (`.scratch/v1-substituir-mobills/research/lacunas-plataforma-e-banco.md`), enviada sem PR. Só fontes primárias, cada afirmação com código de fonte.

- **iOS 26, "Abrir como App Web":** vem ligado por padrão; desligado, vira favorito do Safari. A isenção do ITP de 7 dias está escrita só para app web da Tela de Início; que o favorito a perde é inferência, não está na fonte.
- **ITP no WKWebView:** ligado por padrão em todo WKWebView desde o iOS 14; App-Bound Domains não o desliga. A fonte não diz se os 7 dias valem para conteúdo local de um app Capacitor; o Capacitor avisa que localStorage e IndexedDB podem ser perdidos e recomenda armazenamento nativo.
- **Expo com conta Apple gratuita:** perfil expira em 7 dias, 3 aparelhos; EAS na nuvem e ad hoc exigem conta paga. Release local não está documentado como funcionando com conta gratuita.
- **Android no Brasil:** a verificação vale desde 2026-09-30 para instalações vindas de lojas participantes. A FAQ diz que o sideload direto "ainda não" é afetado; a página de conta limitada (2026-10-23) diz que pacote não registrado deixa de instalar. A divergência continua. Conta limitada: grátis, sem ID, até 20 aparelhos.
- **DSQL:** retomada sem número em segundos (só "mais lenta"); **sem PITR**, só backup completo pelo AWS Backup (restaura em cluster novo).
- **Aurora Serverless v2:** auto-pause documentado por versão de motor, não por região; sa-east-1 tem Serverless v2 nessas versões (auto-pause lá é inferência). Retomada de ~15 s, 30 s+ após 24 h pausado; RDS Proxy impede a pausa.

**Muda os tickets 08 ou 09?** Nada derruba uma opção sozinho.
- 08: guardar dados só no aparelho é arriscado nos três caminhos (PWA com o ajuste desligado, WKWebView do Capacitor); o servidor deve ser a fonte de verdade. Expo e Capacitor no iPhone, sem conta paga, implicam reinstalar a cada 7 dias e ter um Mac.
- 09: a falta de PITR pesa contra o DSQL; as latências de retomada ficam para medir.

Pendências: a parte da conta AWS virou o [ticket 16](16-conferir-credito-e-compartilhamento-na-conta-aws.md) (HITL); as medições e testes reais, o [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md) (HITL).
