# Testes de navegador que falham às vezes na suíte completa

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #166
Origem: [ticket 37](37-cartoes-e-faturas.md): nas rodadas completas de `npx playwright test` (`workers: 1`), quatro testes falharam, um ou outro a cada rodada, e passaram quando rodados sozinhos (`--repeat-each`), um deles também na `main` sem as mudanças do 37:

- `e2e/sem-internet.spec.ts` › "recusado pelo servidor fica 'não enviado: <motivo>'...": `apiResponse.json: Response has been disposed` no `page.route("**/api/contas")` do começo do teste.
- `e2e/sem-internet.spec.ts` › "criado com a resposta perdida e depois editado ou excluído sem internet...": numa rodada, "Salvar" ficou desativado depois do toque no "9"; em outra, o Histórico abriu sem internet com "não foi possível carregar os lançamentos" (sem a última resposta guardada) e o link "Editar" nunca apareceu. O arquivo `sem-internet.spec.ts` sozinho passou 16 de 16 (`--repeat-each=2`).
- `e2e/conflito.spec.ts` › "mudança no mesmo campo vira conflito..." (na `main`, numa worktree limpa).
- `e2e/conflito.spec.ts` › "descartar a minha mudança deixa a versão da outra pessoa", numa rodada em que o log da API não teve nenhum erro.

Uma causa já foi achada e corrigida no PR do ticket 37: no CI, "a exclusão vence a edição" (`e2e/conflito.spec.ts`) deu `IndexError` em `_atual` (`backend/app/lancamentos.py`), porque no Postgres em READ COMMITTED a exclusão da outra pessoa chegava entre as duas leituras e a edição voltava "erro no servidor" em vez de "descartada". Os outros casos acima podem ter a mesma família de causa (leituras em instantes diferentes no Postgres local, que no DSQL não acontecem).

## O que fazer

Achar a corrida de cada um (provável: o teste desliga a rede ou recarrega antes de a leitura ser guardada no aparelho, ou o handler da rota lê a resposta depois de a página navegar) e deixar a suíte estável, sem desligar nem marcar `skip` nenhum teste.

## Checklist

- [ ] Reproduzir na suíte inteira, com `--repeat-each` (`workers: 1`)
- [ ] Corrigir a causa de cada um no teste (ou no app, se for dele) e rodar a suíte completa algumas vezes sem falha
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

- O [ticket 42](42-jornada-completa-do-lancamento-rapido.md) corrigiu três corridas, todas no teste. Em `conflito.spec.ts`, "mudança no mesmo campo", "descartar a minha mudança" e "excluir o que a outra pessoa mudou depois" agora esperam a mudança da outra pessoa subir antes de o aparelho voltar à rede, porque a mudança dele chegava primeiro e o conflito ficava com ela. O último também espera a exclusão subir antes de a outra pessoa recarregar. Em `sem-internet.spec.ts`, "recusado pelo servidor" agora desfaz a rota de `/api/contas` no fim, porque a leitura em andamento estourava no teste seguinte (`route.fetch: Test ended`) e a falha ia para "sem internet, as telas abertas...".
- Ainda falha às vezes: "criado com a resposta perdida e depois editado ou excluído sem internet". O Histórico abre sem a lista guardada. Hipótese: o `sync` do service worker reenvia a fila, que o `page.route` da página não intercepta, e a esvazia antes de a lista do servidor ser guardada.
