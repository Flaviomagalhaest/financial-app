# Testes sem internet intermitentes no CI (saldo da conta e resposta perdida)

Type: task
Status: claimed
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`, `run`
Modelo recomendado: Opus
Effort recomendado: high
Issue: #263
Origem: PR do [ticket 113](113-editar-enquanto-a-criacao-sobe-vira-conflito.md) (31/10). O CI dele falhou num teste que o PR não toca, e a `main` e outros PRs falham num teste vizinho do mesmo arquivo.

## O que falha

- `e2e/sem-internet.spec.ts:336` › "o saldo da conta conta os não enviados do aparelho (criar e excluir) com ⏳ e, ao enviar, fica igual ao do servidor": depois de lançar R$ 45,00 sem internet, o saldo mostra `-R$ 45,00 ⏳` em vez de `-R$ 46,00`, como se o saldo guardado da conta não contasse o R$ 1,00 enviado antes (o teste já tinha visto `-R$ 1,00` sem ⏳). CI: run 197 (PR do 113). Local, na `main` (b2c56b1), sem o 113: 2 de 5 com `--repeat-each=5`.
- `e2e/sem-internet.spec.ts:300` › "criado com a resposta perdida e depois editado ou excluído sem internet: a mudança não se perde": para no "Salvar" (linha 321) ou no `toContainText("− R$ 0,19")` (linha 322). CI: run 189 (`main`, merge do 110) e run 196 (PR do 61).

Só local, com o Postgres de `scripts/postgres-local.sh` já cheio de execuções anteriores (o CI sobe um banco novo a cada run):

- `e2e/lancamentos.spec.ts:134` › "contas: cria com saldo de abertura, renomeia e arquiva...": o botão "Desarquivar conta ..." não aparece depois de arquivar. 5 de 5 na `main` local, depois de umas 300 execuções do arquivo no mesmo banco; no começo da sessão passava.
- `e2e/busca.spec.ts:142` › "sem internet, a busca mostra o que o aparelho guarda...": 1 linha em vez de 2. Uma vez, na suíte inteira.

## Pistas

- Para o `:336`: o saldo guardado das contas é lido de novo depois do envio sem esperar (`void Promise.all(...)` em `enviarAgora`, `web/src/dados/index.ts`, ticket 81). Uma leitura das contas que começou antes de o lançamento subir pode ser guardada depois da leitura nova? A `comTrava("shared")` de `buscarEGuardar` deveria impedir isso; conferir também a leitura que a própria tela "Contas e categorias" faz ao abrir.
- Os dois locais podem ser só o volume de dados do banco local (muitas contas e lançamentos de teste): conferir com um banco novo antes de tratar como bug.

## Checklist

- [ ] Reprodução determinística de cada falha do CI (atraso no `context.route`, como nos tickets 113 e 114)
- [ ] Causa (app ou teste) e correção, com o teste vermelho antes
- [ ] Os dois só locais conferidos num banco novo: bug, ou nota no README sobre limpar o banco local
- [ ] `sem-internet.spec.ts` com `--repeat-each=5` sem falha
- [ ] Verificações do projeto rodando e PR aberto para `main`
