# Telas que filtram a lista guardada passam a ler do servidor

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #397
Origem: [ticket 124](124-historico-sem-a-lista-inteira.md) e [ADR 0024](../../../docs/adr/0024-sem-internet-so-a-janela-do-aparelho.md) (decisão Q6).

## O que construir

Com a [janela do aparelho](166-janela-do-aparelho.md), a lista guardada deixa de ter os meses antigos. Estas telas hoje filtram a lista inteira guardada e precisam ler do servidor, como já fazem os totais:

- **Compras da fatura** (`TelaDaFatura.tsx`): `/api/cartoes/{id}/faturas` dá só os totais; a lista sai do filtro da lista guardada.
- **Ranking e "A escolher" do Mês** (`TelaDoMes.tsx`): o Ranking filtra a lista pelos `lancamento_ids` do mês, e o "A escolher" esconde o item que não está na lista.
- **Parcelas do parcelamento** (`TelaDoParcelamento.tsx`): filtra a lista por `parcelamento_id`; as parcelas antigas de um parcelamento longo saem da janela.

Cada tela guarda a resposta dela no aparelho, como as outras leituras, e soma os não enviados como hoje. Sem internet e sem resposta guardada, a tela diz que precisa de internet, sem mostrar lista vazia como se não houvesse nada.

## Checklist

- [x] Endpoints `GET /api/cartoes/{id}/faturas/{mes}/lancamentos`, `GET /api/meses/{mes}/lancamentos` e `GET /api/parcelamentos/{id}/lancamentos`, com testes do backend (`test_lancamentos_das_telas.py`)
- [x] Fatura, Mês e parcelamento leem do servidor (`useLancamentosDaTela`), com testes de navegador com e sem internet (`telas-leem-do-servidor.spec.ts`)
- [x] Não enviados continuam aparecendo nessas telas sem internet

## Notas

- O índice de estornos da Fatura ainda olha a lista guardada (o estorno pode estar em outra fatura): fica para o [ticket 166](166-janela-do-aparelho.md), que já cobre o índice de estornos.
