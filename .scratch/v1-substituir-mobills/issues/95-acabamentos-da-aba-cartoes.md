# Acabamentos da aba Cartões

Type: task
Status: ready-for-agent
Blocked by: nenhum
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #189
Origem: revisão do [ticket 55](55-aba-cartoes.md) (aba Cartões)

## O que construir

Pontos que a revisão do 55 deixou de lado por serem de julgamento.

## Checklist

- [ ] "Anterior" e "Próxima" são as vizinhas na lista de faturas, não o mês adjacente: se faltar uma fatura no meio (mês sem compra), o rótulo engana. Decidir entre mostrar o mês ou só rotular pela posição
- [ ] Compra criada só no aparelho ainda não tem `mes` e some do detalhe da fatura até subir; mostrá-la pelo `fatura_mes` ou pela data, com a regra do ADR 0003
- [ ] Cada fatura é uma linha própria (hoje: até três por cartão) e a linha toda é tocável, não só o "Abrir"
- [ ] `mesPorExtenso` (`web/src/cartoes/apresentacao.ts`) repete `rotuloDaFatura` (`web/src/lancamentos/datas.ts`): um helper só
- [ ] Conferir com o dono se a aba mostra só titulares (o adicional cai na fatura do titular)
