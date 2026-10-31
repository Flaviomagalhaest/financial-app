# Aviso de planejamento: sobras do ticket 109

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #249
Origem: [ticket 109](109-aviso-de-planejamento-casos-que-o-aparelho-nao-sabe.md): achados da revisão que ficaram fora dele

## Checklist

- [x] **Teste do cartão arquivado**: compra não enviada num cartão arquivado conta pela fatura — teste de navegador em `aviso-de-planejamento.spec.ts` (a compra entra na fila antes do arquivamento, sem internet; sem o `?arquivados=true` o aviso cai no mês da data e o teste falha). O app já marca essa compra como "cartão arquivado" e oferece "Corrigir", e o aviso segue valendo nela
- [x] **Teste do hook para o criar sem resposta**: teste de navegador (lote perdido depois de o servidor gravar; fila com `tentadoEm`/`talvezNoServidor`; lista de lançamentos ainda sem o criar e planejamento já com ele) — o aviso conta uma vez; sem `semContarDeNovo` o teste vê 20% em vez de 10%
- [x] **Recorrência enviada sem resposta** (`criar_recorrencia` com `talvezNoServidor`): sem contagem dupla — `contagensNoAparelho` só lê itens de lançamento (`deLancamento`), então a regra na fila não entra no aviso, nem enviada nem não; o previsto dela só aparece depois que o servidor a expande
- [x] **Tela de transferência**: o item de transferência é um valor a guardar, não um que se evita passar; o texto agora é o da receita ("Faltam R$ X para o planejado", "Chega ao planejado", "R$ X acima do planejado"; `oQueSobra` ganhou `transferencia`, com teste de tabela). A tela só escolhe uma categoria, então nunca há item a escolher e o `onEscolher` vazio fica, com comentário
- [x] **ADR 0018**: uma linha dizendo que o aparelho lê também os cartões arquivados para achar a fatura
- [ ] Verificações do projeto rodando e PR aberto para `main`
