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

- [x] "Anterior" e "Próxima" são as vizinhas na lista de faturas, não o mês adjacente: se faltar uma fatura no meio (mês sem compra), o rótulo engana. Decidir entre mostrar o mês ou só rotular pela posição
- [x] Compra criada só no aparelho ainda não tem `mes` e some do detalhe da fatura até subir; mostrá-la pelo `fatura_mes` ou pela data, com a regra do ADR 0003
- [x] Cada fatura é uma linha própria (hoje: até três por cartão) e a linha toda é tocável, não só o "Abrir"
- [x] `mesPorExtenso` (`web/src/cartoes/apresentacao.ts`) repete `rotuloDaFatura` (`web/src/lancamentos/datas.ts`): um helper só
- [ ] Conferir com o dono se a aba mostra só titulares (o adicional cai na fatura do titular)
- [ ] Testes de navegador dos itens acima (só `tsc` rodou na sessão; o e2e precisa de API e banco)
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Rótulo: "Anterior"/"Próxima" só quando a vizinha é o mês adjacente; senão "Antes"/"Depois". O mês aparece sempre.
- Compra sem `mes` entra pela fatura escolhida ou pela data (`mesEmQueConta`, ADR 0003).
- Linha da fatura é um só link; `mesPorExtenso` agora vive em `lancamentos/datas.ts`.
- O item sobre adicionais segue aberto (precisa do dono): a aba hoje mostra só titulares.
