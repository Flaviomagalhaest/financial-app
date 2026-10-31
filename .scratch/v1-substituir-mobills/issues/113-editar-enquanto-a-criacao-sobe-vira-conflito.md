# Editar o lançamento enquanto a criação sobe vira conflito falso

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: high
Issue: #235
Origem: revisão do CI pedida pelo dono (30/10): `e2e/lancamentos.spec.ts` › "cria, edita e exclui um lançamento simples e o vê na lista" quebra PRs e a própria `main` com a linha "⚠ conflito: sua mudança espera decisão" logo depois de editar o lançamento que acabou de ser criado. Na `main`: runs 137 (merge do 62) e 153 (merge do 81); nos PRs: run 154 (85, duas tentativas) e as listadas no [ticket 90](90-teste-do-recusado-intermitente.md) (runs 70, 84, 125). O 90 fechou sem pegar esta causa.

## Causa

É do app, não do teste nem do PR que roda o CI.

1. A tela de edição (`TelaDeLancamento.tsx`) guarda o lançamento **uma vez**, quando ele aparece (`setExistente(achado)`), para o envio da fila não apagar o que se digita.
2. Se a tela abre enquanto a criação ainda sobe, o guardado é o da fila (`naoEnviado: true`, sem `versao`).
3. A criação chega, e `aplicar` (`dados/fila.ts`) tira o item da fila.
4. Ao salvar, `baseDe(existente)` (`dados/index.ts`) devolve `undefined`, porque o guardado é "não enviado", e na fila não há mais item. `pedidoDeSalvar` monta `{ acao: "editar", base: undefined }`.
5. `alteracao` sem base manda todos os campos sobre a **versão 0**. No servidor (`editar`, `lancamentos.py`), o campo nasceu na versão 1 > 0 e o valor mudou: conflito com a própria criação.

No CI, a ida e volta da criação demora o bastante para o teste abrir "Editar" no meio dela; na máquina livre, raramente.

## Reprodução determinística

Um teste que atrasa a primeira resposta de `/api/lancamentos/lote` (com `page.context().route`, porque o `page.route` não pega o que passa pelo service worker), abre "Editar" enquanto a linha mostra "não enviado", espera a criação chegar (≈2,5 s), muda o valor e salva. Depois que o "não enviado" some, a linha mostra o conflito: 3 de 3 na `main` (8348620). O lote da edição sai com `"versao": 0` e todos os campos. Sem o atraso, `lancamentos.spec.ts` falhou 2 de 5 e 3 de 6 localmente (`--repeat-each`), antes e depois do merge do 81.

Ao escrever o teste, o `not.toContainText("conflito")` só vale depois de esperar o "não enviado" sumir; antes disso ele passa na hora.

## O que fazer

A edição precisa subir sobre a versão que a criação deste aparelho gerou, e não sobre a 0. Cuidado para não esconder um conflito de verdade: se a outra pessoa mudou o lançamento entre a criação chegar e o "Salvar", isso continua sendo conflito. Caminhos possíveis, a decidir na implementação:

- ao salvar sem item na fila, usar como base o lançamento do servidor que a criação gerou (a lista guardada o tem, versão 1), e não o que estiver mais novo;
- ou `aplicar` deixar registrado, para quem guardou o "não enviado", a versão com que o pedido foi aceito.

Confira também os outros caminhos que usam `baseDe` com um guardado "não enviado": `excluirLancamento` (sem base, a exclusão sobe sem `versao` e pula a checagem de conflito) e `confirmarPrevisto`.

## Checklist

- [ ] Teste de navegador determinístico (o da reprodução acima), vermelho antes da correção
- [ ] Teste de unidade do caminho na fila (`fila.ts`), se a correção ficar lá
- [ ] Correção; a mudança da outra pessoa no meio continua virando conflito (teste)
- [ ] `lancamentos.spec.ts` com `--repeat-each=10` sem falha
- [ ] Verificações do projeto rodando e PR aberto para `main`
