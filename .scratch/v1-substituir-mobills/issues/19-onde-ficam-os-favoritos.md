# Onde ficam os favoritos no lançamento rápido

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` (HITL: precisa do dono); apoio: `prototype` se a resposta pedir ver na tela
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #37
Origem: veredito do [ticket 10](10-fluxo-de-lancamento-rapido.md): o casal escolheu a variante A (valor primeiro), que não tinha favoritos, e pediu para decidir o lugar deles na spec

## Question

Na tela de novo lançamento da variante A (valor primeiro), onde ficam os favoritos, e o que um favorito preenche?

Opções vistas no ticket 10: uma fileira de favoritos acima do teclado, ao lado do "repetir último", enquanto o lançamento está vazio; uma grade na tela inicial, como na variante C (só aparece para quem abre o app, não pelo atalho do Android); ou os dois. Falta também decidir se o favorito traz o valor (como o "repetir último") ou deixa o valor para o teclado, e como um lançamento vira favorito.

## Checklist

- [x] Lugar dos favoritos e o que eles preenchem, decididos com o dono, em `## Answer`
- [x] Como um lançamento vira favorito (marcar à mão ou os mais usados)

## Answer

O casal escolheu a **variante C do protótipo: os favoritos ficam nos dois lugares**, com a mesma lista. Protótipo na branch `prototipo/favoritos` (`.scratch/v1-substituir-mobills/prototipos/19/favoritos.html`, publicado em https://claude.ai/artifact/Y6tmazHzZAB2pins6zeG2P).

- **Lugar**: uma fileira que rola de lado acima do teclado da tela de novo lançamento, ao lado do "repetir último", enquanto o lançamento está vazio (vale também para quem entra pelo atalho do Android); e uma grade na tela inicial (vale para quem abre o app, inclusive no iPhone). Fileira e grade mostram a mesma lista.
- **O que o favorito preenche**: tudo, inclusive o valor. Ao tocar, abre a tela de novo lançamento já preenchida (conta, categorias, tags, pessoa e valor) e o valor é só o padrão: dá para trocá-lo pelo teclado, e **"Salvar" é a confirmação**. Não há uma folha separada nem salvamento direto.
- **Qual é o valor padrão**: o valor do último lançamento daquele favorito, atualizado a cada uso.
- **Como vira favorito**: os dois jeitos. Marcação à mão (⭐ no lançamento e, depois de salvar, o app oferece "Favoritar") e sugestão automática dos mais usados.
- **Marcados e sugeridos juntos**: os marcados vêm primeiro, na ordem da marcação, sem limite fixo. Os **sugeridos** ficam num grupo à parte, rotulado "Sugeridos": os 3 lançamentos mais repetidos que ainda não são favoritos, só depois de 5 usos. Tocar na ⭐ de um sugerido o promove a favorito; dá para dispensar um sugerido.
- **Gerenciar**: reordenar e remover favoritos ficam nas configurações.

Fica para a spec: os números 3 (sugeridos) e 5 (usos) são valores iniciais, a ajustar com o uso; e a tela de configurações dos favoritos não foi prototipada.
