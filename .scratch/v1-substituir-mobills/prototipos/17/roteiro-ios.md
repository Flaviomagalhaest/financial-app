# Roteiro iOS 26: "Abrir como App Web" e perda de dados do PWA

O teste do ITP de 7 dias saiu daqui e está em `../19/roteiro-itp.md` (ticket 19).

Aparelho: iPhone real com iOS 26. Anote a versão exata (Ajustes > Geral > Sobre).
Use uma página HTTPS qualquer que grave um valor em `localStorage`, em IndexedDB e na Cache API (pode ser um `index.html` simples), com o carimbo de data/hora da gravação.

## A. "Abrir como App Web" ligado e desligado

1. Safari: abra a página, grave os dados, Compartilhar > Adicionar à Tela de Início.
2. Com "Abrir como App Web" **ligado** (padrão do iOS 26): abra pelo ícone, confira que os dados existem, feche.
3. Ajustes > Apps > Safari (ou o ícone na Tela de Início) > desligue "Abrir como App Web". Abra pelo ícone de novo.
4. Registre: os dados do passo 2 continuam? O ícone abre no Safari ou em janela própria? Há login/sessão preservada?
5. Religue a opção e registre se os dados voltam.
6. Repita 1-5 em um segundo ícone criado já com a opção desligada.

## Formato do resultado (copiar para `## Answer` do ticket)

| Cenário | iOS | Dados sobreviveram? | Observação |
|---|---|---|---|
