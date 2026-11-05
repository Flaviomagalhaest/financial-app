# Aviso de planejamento da parcela do meio aparece de vez em quando no teste

Type: task
Status: claimed
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`, `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #460
Origem: [ticket 181](../../v1-substituir-mobills/issues/181-regra-descartada-depois-da-pagina-fechada.md), falha do CI do PR #458 (job `verificar`, 1ª execução; verde ao reexecutar).

## O problema

`web/e2e/parcelamento.spec.ts`, "a tela do parcelamento com a lista sem a 1ª parcela não calcula o aviso de planejamento com a parcela do meio", falhou uma vez no CI na linha 608: `getByRole("region", { name: "Aviso de planejamento" })` com 1 elemento, esperado 0. O parcelamento do teste é criado pela API (sem a fila), e o mesmo teste passou 6 de 6 na sessão do 181 e na reexecução do CI.

Hipótese, não verificada: o arquivo não bloqueia o service worker (`serviceWorkers: "block"`), e a leitura dele de `/api/parcelamentos/<id>/lancamentos` não passa pelo `page.route` do teste. Ela traz a 1ª parcela de volta e a tela calcula o aviso com a lista inteira.

## Checklist

- [ ] Reproduzir com taxa alta (por exemplo, `--repeat-each` com a leitura do service worker forçada antes da da página)
- [ ] Corrigir o teste (bloquear o service worker no teste ou rotear no contexto), sem desligá-lo
