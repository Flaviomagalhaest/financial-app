# Roteiro iOS 26: perda de dados do PWA e ITP

Aparelho: iPhone real com iOS 26. Anote a versão exata (Ajustes > Geral > Sobre).
Use uma página HTTPS qualquer que grave um valor em `localStorage`, em IndexedDB e na Cache API (pode ser um `index.html` simples), com o carimbo de data/hora da gravação.

## A. "Abrir como App Web" ligado e desligado

1. Safari: abra a página, grave os dados, Compartilhar > Adicionar à Tela de Início.
2. Com "Abrir como App Web" **ligado** (padrão do iOS 26): abra pelo ícone, confira que os dados existem, feche.
3. Ajustes > Apps > Safari (ou o ícone na Tela de Início) > desligue "Abrir como App Web". Abra pelo ícone de novo.
4. Registre: os dados do passo 2 continuam? O ícone abre no Safari ou em janela própria? Há login/sessão preservada?
5. Religue a opção e registre se os dados voltam.
6. Repita 1-5 em um segundo ícone criado já com a opção desligada.

## B. ITP de 7 dias

1. Com a página como aba do Safari (não instalada), grave os dados e não abra mais o site.
2. Passados 8 dias sem interação, abra e registre se `localStorage`, IndexedDB e Cache API sumiram.
3. Repita com o PWA instalado (opção ligada) sem abrir por 8 dias.
4. Plano B (Capacitor/WKWebView): só se o dono quiser testar; um app de teste com conteúdo local em WKWebView, 8 dias sem abrir, e registrar se os dados persistem.

## Formato do resultado (copiar para `## Answer` do ticket)

| Cenário | iOS | Dados sobreviveram? | Observação |
|---|---|---|---|
