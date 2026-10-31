# Edição em lote: conferir as regras provisórias

Type: grilling
Status: ready-for-human
Blocked by: 61
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se uma regra mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #251
Origem: [ticket 61](61-edicao-em-lote.md): a spec (histórias 147 a 151), o [ticket 24](24-busca-e-filtros-salvos.md) e o [ADR 0013](../../../docs/adr/0013-busca-por-data-da-compra-e-fatura-a-parte.md) não dizem o que fazer nestes casos, e a implementação escolheu um comportamento provisório para cada um (em `backend/app/edicao_em_lote.py`, com teste em `backend/tests/test_edicao_em_lote.py`, e na tela em `web/src/busca/`)

## As perguntas

1. **Quem o desfazer pula.** A história 151 diz "pulando o que a outra pessoa mudou depois". O desfazer pula o lançamento cujas categorias, tags ou escolha de item **qualquer pessoa** mudou depois do lote, inclusive quem fez o lote, para não desfazer uma correção feita à mão depois. Mudar valor, data ou descrição não conta. Fica assim, ou o desfazer deveria passar por cima do que a própria pessoa mudou?
2. **Quem pode desfazer.** Qualquer um do casal desfaz qualquer edição em lote, a sua ou a da outra pessoa. A lista (`#/edicoes-em-lote`) mostra quem fez.
3. **Categoria de outro tipo.** Acrescentar ou substituir por uma categoria de despesa numa seleção que tem receitas não recusa o lote: as receitas ficam com as categorias que têm, e a prévia diz quantas ("ficam com as categorias que têm: a categoria pedida é de outro tipo"). Recusar o lote seria mais seguro, mas "todos do resultado" com tipos misturados ficaria inútil.
4. **Estorno.** O estorno segue a compra ([ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md): leva as mesmas categorias e tags): marcar a compra leva os estornos dela, e o estorno marcado sem a compra fica de fora, com a contagem na prévia.
5. **Transferências.** Ficam fora do lote, mesmo em "todos do resultado" e mesmo tendo categoria (de transferência). A spec só fala em lançamentos.
6. **Categoria e tag arquivadas.** Pedir para acrescentar (ou trocar por) uma categoria ou tag arquivada recusa o lote inteiro, mesmo que todos os marcados já a tenham. Tirar uma arquivada pode.
7. **Categoria ou tag que sumiu.** Se uma categoria ou tag que o lançamento tinha antes do lote foi juntada a outra ou excluída depois, o desfazer pula o lançamento ("uma categoria ou tag que ele tinha foi juntada a outra ou excluída"), em vez de voltar só o resto.
8. **A amostra da prévia.** São os 5 primeiros que mudam pela data, do mais recente ao mais antigo, e não na ordem escolhida na busca ("Maior valor").
9. **Uma mudança por vez na tela.** A API aceita categorias e tags no mesmo lote, e o desfazer volta as duas juntas; a folha muda só uma das duas por vez (o casal faz dois lotes).
10. **A lista de edições.** Mostra só as que ainda se desfazem (até 30 dias, não desfeitas). A desfeita some da lista, e não há histórico das edições antigas na tela.
11. **A contagem enquanto se marca.** A barra da seleção diz "2 marcados" (as linhas marcadas); o "12 compras (58 lançamentos)" da história 149 só aparece na prévia, que é quando o servidor expande os parcelamentos e os estornos. Mostrar já na barra pediria uma chamada a cada marcação.
12. **O parcelamento muda junto.** O lote muda também a classificação guardada no parcelamento (a com que as parcelas voltam quando ele cresce), e o desfazer a volta se ninguém a mudou depois. A parcela que o parcelamento reviveu depois do lote conta como mudada depois e fica como está.
13. **Valores.** 30 dias (`desfazerEdicaoEmLoteDias`, da spec) e 5 na amostra (`amostraDaEdicaoEmLote`, da spec); o lote grava 50 lançamentos por transação (`POR_TRANSACAO`), a conferir no DSQL no [ticket 35](35-teste-nos-dois-celulares.md).

## Checklist

- [ ] O dono responde cada pergunta e a resposta vai para `## Answer`
- [ ] Se uma regra mudar: teste de API em `backend/tests/test_edicao_em_lote.py`, ajuste em `backend/app/edicao_em_lote.py` e na tela (`web/src/busca/`), e o README (seção Busca) acompanha
