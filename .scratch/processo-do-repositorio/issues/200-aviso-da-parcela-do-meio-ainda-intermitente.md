# Aviso da parcela do meio ainda falha de vez em quando no teste

Type: task
Status: claimed
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`, `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #504
Origem: [ticket 158](../../v1-substituir-mobills/issues/158-mudar-as-partes-pela-tela-do-parcelamento.md), ao integrar a `main` na branch do PR #489; continuação do [ticket 185](185-aviso-da-parcela-do-meio-intermitente.md).

## O problema

O teste "a tela do parcelamento com a lista sem a 1ª parcela não calcula o aviso de planejamento com a parcela do meio" (`web/e2e/parcelamento.spec.ts`, bloco "sem service worker") ainda falha de vez em quando no `toHaveCount(0)` do aviso de planejamento, mesmo com o service worker bloqueado pelo 185. No local, com `--repeat-each 6 -g "sem a 1ª parcela"`, falhou 4 de 6 vezes na `main` pura (origin/main de 2026-11-07) e na branch do 158, também com o banco recriado. O CI do PR #489 passou nele.

## Checklist

- [ ] Achar a causa (a leitura de antes, com a 1ª parcela, ainda na memória? o `page.route` chegando depois da releitura?) e corrigir o teste ou a tela
- [ ] O teste verde com `--repeat-each 10`; verificações do projeto e PR para `main`
