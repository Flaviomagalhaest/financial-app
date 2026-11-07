# Recorrência grava o aviso da ocorrência pulada pela fatura paga

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`, `domain-modeling`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #482
Origem: decisão do [ticket 184](184-aviso-da-ocorrencia-que-a-fatura-paga-tirou.md)

## O que fazer

Quando `_gerar_um_lote` (`backend/app/recorrencias.py`) passa, sem lançar, pela ocorrência de antes de hoje que cairia numa fatura paga (ADR 0021, ticket 179), a regra grava um aviso de texto, no padrão de `mudanca_recusada` / `tirar_a_recusa` do parcelamento (`backend/app/parcelamentos.py`).

- O aviso só informa: data da ocorrência, titular e mês da fatura paga, e "lance à mão se precisar". Não refaz a ocorrência nem volta `geradas`.
- Outra ocorrência pulada antes da dispensa junta a data no mesmo aviso.
- O aviso fica até o casal dispensar: operação e endpoint de dispensa (como `tirar_a_recusa`).
- A leitura da regra devolve o aviso.

## Checklist

- [x] Teste primeiro em `backend/tests/test_fatura_paga.py`: pagamento entre os lotes grava o aviso; segunda ocorrência acumula; dispensa limpa
- [x] Migration da coluna na recorrência
- [x] Gravar o aviso em `_gerar_um_lote`
- [x] Endpoint de dispensa e campo na leitura da regra (atualizar `esquemas_do_formato.json`/exportação se a coluna entrar no formato)
- [x] ADR 0021: a ocorrência pulada deixa aviso na regra
- [x] `GLOSSARY.md`: termo "ocorrência pulada pela fatura paga"

## Notes

- A coluna `recorrencias.puladas_pela_fatura_paga` guarda uma ocorrência por linha (data, titular e mês); a leitura monta o aviso em `aviso_da_fatura_paga`. A mesma data não entra duas vezes. Formato do backup na versão 35.
- Dispensa: `DELETE /api/recorrencias/{id}/aviso-da-fatura-paga` (204; 404 sem a regra).
- Se a geração voltar a passar por uma ocorrência já dispensada (o `geradas` recua por um fim que tirou um atrasado e depois foi estendido, caso raro), o aviso volta com ela: é a mesma informação, e o casal o dispensa de novo.
- Fica para o [ticket 193](193-tela-da-regra-mostra-o-aviso-da-ocorrencia-pulada.md): a tela da regra mostra o aviso e chama a dispensa.
