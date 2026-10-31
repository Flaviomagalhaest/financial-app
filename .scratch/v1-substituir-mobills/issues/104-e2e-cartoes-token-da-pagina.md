# e2e cartoes.spec.ts:87 estoura o tempo ao pegar o token da página

Type: bug
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`, `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #210
Origem: [ticket 82](82-rede-que-nao-responde-e-tempo-limite.md) (o teste já falhava na `main` antes da mudança do 82, nesta máquina)

## O problema

`tokenDaPagina` (`web/e2e/cartoes.spec.ts:19`) espera um pedido a `/api/` com `Authorization` depois do `page.reload()` e estoura os 30 s. Os outros testes passam.

## Checklist

- [x] Achar a causa (token já em cache no recarregamento? pedido saindo antes do `waitForRequest`?) e corrigir

## Resolução

Não reproduzido: `npx playwright test cartoes.spec.ts --repeat-each=8` passou 16 de 16 numa máquina limpa (Postgres local, `npm ci`). A causa era o `reload` cortar o login no meio, sem nenhum pedido com token; já está tratada na `main` pela espera do botão "Sair" em `tokenDaPagina` (`web/e2e/api.ts`) e pela espera do título "Cartões" nos testes. Nenhuma mudança de código.
