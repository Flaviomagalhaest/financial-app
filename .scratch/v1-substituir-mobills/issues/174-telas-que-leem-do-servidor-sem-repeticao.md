# Telas que leem do servidor: uma definição por tela, sem repetição

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `codebase-design`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #418
Origem: revisão do [ticket 165](165-telas-que-filtram-a-lista-leem-do-servidor.md) (PR #404), cheiros de código marcados como julgamento e deixados de fora do PR.

## O que construir

As três telas do 165 (`TelaDaFatura.tsx`, `TelaDoMes.tsx`, `TelaDoParcelamento.tsx`) repetem o mesmo trio e o hook `useLancamentosDaTela` (`web/src/dados/index.ts`) pede o caminho e a leitura em separado:

- o caminho da resposta guardada e a rota do `api.GET` ficam escritos duas vezes e podem divergir; `relerAsParcelas` monta o caminho do parcelamento de novo à mão. Juntar caminho e leitura num lugar só, usado pelas telas e por `relerAsParcelas`.
- os avisos "Sem internet: ... da última leitura" e "Sem internet: ... precisam de internet" se repetem quase iguais nas três telas. Um componente ou texto compartilhado.
- nomes que confundem: em `TelaDaFatura.tsx`, `lancamentos` (lista guardada, só para o índice de estornos), `daLeitura` e `compras`; em `TelaDoMes.tsx`, `lancamentosDeAntes`. Renomear para dizer a fonte.
- o filtro `daFatura` repete no cliente a regra de "mês em que conta" do servidor, só para a fila: deixar um comentário apontando para a [ADR 0018](../../../docs/adr/0018-aviso-de-planejamento-repete-regras-do-servidor-so-para-mostrar.md), se for ela que admite a repetição.

Sem mudar comportamento: os testes de `web/e2e/telas-leem-do-servidor.spec.ts` seguem passando como estão.

## Checklist

- [x] Caminho e leitura de cada tela definidos uma vez
- [x] Aviso "Sem internet" compartilhado
- [x] Nomes que dizem a fonte da lista
- [ ] `telas-leem-do-servidor.spec.ts`, `cartoes.spec.ts`, `mes.spec.ts` e `parcelamento.spec.ts` passando
