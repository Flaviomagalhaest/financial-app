# Teste de navegador do lançamento recusado falha às vezes

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #166
Origem: [ticket 37](37-cartoes-e-faturas.md): numa rodada completa de `npx playwright test`, `e2e/sem-internet.spec.ts` › "recusado pelo servidor fica 'não enviado: <motivo>'..." falhou com `apiResponse.json: Response has been disposed`, no `page.route("**/api/contas")` do começo do teste; sozinho, passou 3 de 3 (`--repeat-each=3`)

## O que fazer

Achar por que a resposta de `rota.fetch()` é descartada antes do `resposta.json()` (provável: a página recarrega ou navega enquanto o handler da rota ainda lê a resposta) e deixar o teste estável, sem desligá-lo nem marcá-lo como `skip`.

## Checklist

- [ ] Reproduzir com `--repeat-each` na suíte inteira (`workers: 1`)
- [ ] Corrigir a causa no teste (ou no app, se for dele) e rodar a suíte algumas vezes sem falha
- [ ] Verificações do projeto rodando e PR aberto para `main`
