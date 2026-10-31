# Teste "confirmar com ajuste" não espera a confirmação da outra pessoa chegar

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #236
Origem: revisão do CI pedida pelo dono (30/10): `e2e/conflito.spec.ts:169` › "confirmar com ajuste o que a outra pessoa já confirmou leva à tela de conflito" é a falha mais comum dos PRs: runs 140 (95), 143 (59), 151 (81), 153 (`main`, merge do 81) e 154 (85). O erro é sempre o mesmo: o botão "O de Fulana, às HH:MM: R$ 1,00" não aparece, porque não houve conflito.

## Causa

Está no teste. Ela confirma pela fila (ticket 83), e o `expect(linha(dela, descricao)).toHaveCount(0)` passa assim que a confirmação entra na fila do aparelho dela, antes de subir. Se a confirmação com ajuste dele chega ao servidor primeiro, ela vale sem conflito, e é a confirmação dela que encontra o previsto já confirmado.

O [ticket 90](90-teste-do-recusado-intermitente.md) corrigiu o fim deste teste (espera o "não enviado" sumir), mas não este começo.

## Reprodução determinística

Com um atraso de 1,5 s **antes** do `route.fetch()` em `contextoDela.route("**/api/lancamentos/lote", ...)`, o teste falha 2 de 2 com o erro do CI. Atrasar só a resposta não reproduz, porque o servidor já gravou.

## O que fazer

- Depois de ela confirmar, esperar a confirmação chegar ao servidor antes de ele ajustar: por exemplo, recarregar a tela dela até o lançamento aparecer realizado no Histórico (`toPass`, como o 90 fez em "excluir o que a outra pessoa mudou depois"). O `nao-enviados` a 0 não serve: passa antes de a fila ser lida (nota do 90).
- Procurar o mesmo padrão nos outros testes de duas pessoas (`conflito.spec.ts`, `pessoa-e-repetido.spec.ts`, `aviso.spec.ts`): uma ação de um lado que só é conferida na tela de quem a fez. Exemplos já vistos no CI: "a exclusão vence a edição" (run 140; nota do ticket 83 no 90) e "'Excluir este' tira o lançamento repetido para os dois" (run 153: a outra tela ainda tinha 2 linhas depois do `reload`).

## Checklist

- [ ] O teste com o atraso acima passa (fica como teste ou como verificação local, a decidir). O PR do [ticket 98](98-parcelamento-criar-pela-tela-e-sem-internet.md) trouxe a correção, porque o teste derrubava o CI dele: depois de ela confirmar, o teste pergunta ao servidor (`apiDaPagina(dela)`, `expect.poll`) até o lançamento estar realizado. Com o atraso de 1,5 s, falhou sem a correção e passou 2 de 2 com ela, como verificação local; o atraso não ficou no teste
- [ ] Os outros testes de duas pessoas com o mesmo padrão corrigidos. O PR do [ticket 98](98-parcelamento-criar-pela-tela-e-sem-internet.md) já corrigiu os dois de `pessoa-e-repetido.spec.ts` ("'Parece repetido' aparece só para quem recebeu..." e "'Excluir este' tira..."), que falhavam no CI da `main`: eles recarregam a outra tela até a fila de quem mudou chegar ao servidor (`toPass`)
- [ ] `conflito.spec.ts` e `pessoa-e-repetido.spec.ts` com `--repeat-each=5` sem falha
- [ ] Verificações do projeto rodando e PR aberto para `main`
