# Parcelamento: classificação da correção interrompida não é refeita pela tarefa diária

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #246
Origem: [ticket 103](103-parcelamento-correcao-interrompida-e-corrida.md) (revisão com sub-agentes: o que o 103 deixou como está)

## O que construir

Quando o `PATCH /api/parcelamentos/{id}` cai depois de gravar o parcelamento e antes de refazer as parcelas, a tarefa diária refaz o cronograma (valor, data, fatura, as que saem e as que voltam), mas não a classificação (descrição, categorias, tags, pessoa, item): o pedido não guarda quais campos trouxe, e refazer tudo desfaria a descrição que alguém corrigiu numa parcela só. Hoje o parcelamento fica com a descrição nova e as parcelas com a antiga até alguém repetir o pedido com o campo; um PATCH só de valor também não a corrige.

## Checklist

- [x] Gravar a intenção (quais campos de classificação o pedido trouxe) para o refazer continuar, ou outro jeito de a tarefa diária saber o que destoa por causa da correção e não por edição à mão da parcela
- [x] Testes de API (correção só de classificação interrompida, concluída pela tarefa diária, sem desfazer a edição à mão de outra parcela)
- [x] Verificações do projeto rodando e PR aberto para `main`

## Comments

Decisões da implementação:

- **Intenção gravada**: coluna `parcelamentos.classificacao_pendente` (migration 0055), os campos de classificação que o pedido trouxe, separados por vírgula. O `_mudar` grava a união com o que já estava pendente; quem termina o refazer (o próprio PATCH ou a tarefa diária) zera a coluna só se ela ainda tiver o valor com que refez (`_dar_por_refeita`), para uma correção concorrente não perder a dela.
- **Tarefa diária**: `_falta_conserto` e `_reajustar_do_parcelamento` passam o pendente para `_correcoes`; a edição à mão de campos que o pedido não trouxe segue intocada, e depois de concluída a correção a descrição editada numa parcela só não volta.
- **PATCH só de valor** termina também a classificação que uma correção anterior deixou pendente.
- **Backup**: a coluna sobe o formato para 22 (conversor 21→22 preenche vazio; esquema em `esquemas_do_formato.json`).
- **Limite conhecido**: o zerar compara o texto da coluna. Dois PATCH quase simultâneos que trazem os mesmos campos deixam o texto igual, e o fim do refazer do primeiro pode zerar a intenção do segundo antes de ele terminar; se o segundo cair nessa janela, a tarefa diária não refaz a classificação dele e basta repetir o pedido. Exigiria dois pedidos do casal no mesmo segundo sobre os mesmos campos, então fica assim.
- O zerar roda logo depois do refazer das parcelas e antes de gerar as que faltam (a geração já cria com a classificação inteira), para uma queda na geração não deixar a intenção presa.
