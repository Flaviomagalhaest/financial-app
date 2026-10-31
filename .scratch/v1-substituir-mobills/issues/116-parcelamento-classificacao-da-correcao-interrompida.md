# Parcelamento: classificação da correção interrompida não é refeita pela tarefa diária

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #246
Origem: [ticket 103](103-parcelamento-correcao-interrompida-e-corrida.md) (revisão com sub-agentes: o que o 103 deixou como está)

## O que construir

Quando o `PATCH /api/parcelamentos/{id}` cai depois de gravar o parcelamento e antes de refazer as parcelas, a tarefa diária refaz o cronograma (valor, data, fatura, as que saem e as que voltam), mas não a classificação (descrição, categorias, tags, pessoa, item): o pedido não guarda quais campos trouxe, e refazer tudo desfaria a descrição que alguém corrigiu numa parcela só. Hoje o parcelamento fica com a descrição nova e as parcelas com a antiga até alguém repetir o pedido com o campo; um PATCH só de valor também não a corrige.

## Checklist

- [ ] Gravar a intenção (quais campos de classificação o pedido trouxe) para o refazer continuar, ou outro jeito de a tarefa diária saber o que destoa por causa da correção e não por edição à mão da parcela
- [ ] Testes de API (correção só de classificação interrompida, concluída pela tarefa diária, sem desfazer a edição à mão de outra parcela)
- [ ] Verificações do projeto rodando e PR aberto para `main`
