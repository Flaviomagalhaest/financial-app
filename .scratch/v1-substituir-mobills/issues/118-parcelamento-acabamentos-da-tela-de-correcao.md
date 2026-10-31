# Parcelamento: acabamentos da tela de correção

Type: task
Status: ready-for-agent
Blocked by: 98
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #255
Origem: [ticket 98](98-parcelamento-criar-pela-tela-e-sem-internet.md) (o que a tela de correção do parcelamento deixou de fora)

## O que construir

A tela `#/parcelamento/<id>` (`web/src/lancamentos/TelaDoParcelamento.tsx`) corrige descrição, valor, parcelas, data, categorias, tags e pessoa pelo `PATCH /api/parcelamentos/{id}` e exclui pelo `DELETE`, com internet. Faltam três coisas que a tela de lançamento já tem.

## Checklist

- [ ] Escolha do item do planejamento (`item_categoria_id` no `PATCH`): com duas ou mais categorias com item no mês, a correção não pergunta, e as parcelas ficam "a escolher"; repetir o `AvisoDePlanejamento` da tela de lançamento (`useAvisoDePlanejamento` em `web/src/dados/index.ts`)
- [ ] Criar tag nova na correção: hoje ela só marca e desmarca as tags que já existem
- [ ] Juntar o campo "Nova tag" (`criarTag`, `mesmaTag`) de `FolhaDeDetalhes.tsx`, `TelaDaRecorrencia.tsx` (ticket 120) e do parcelamento num componente só, em vez de uma terceira cópia
- [ ] Abrir a tela sem internet num parcelamento que o aparelho nunca leu mostra "Sem internet: este parcelamento não está no aparelho." (`/api/parcelamentos` só é guardado quando a tela abre ou quando um parcelamento sobe pela fila); guardar a leitura no `iniciarEnvioAutomatico`, como os favoritos, ou montar a tela pelas parcelas guardadas
- [ ] Testes de navegador em `web/e2e/parcelamento.spec.ts`
- [ ] Verificações do projeto rodando e PR aberto para `main`
