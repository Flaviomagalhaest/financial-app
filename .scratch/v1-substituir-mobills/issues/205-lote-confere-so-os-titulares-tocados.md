# Lote de ações confere só os titulares tocados pela gravação

Type: task
Status: ready-for-human
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #536
Origem: [ticket 202](202-decidir-o-custo-da-protecao-no-dsql.md): decisão do dono (08/11): o custo da proteção da fatura paga pesa só no lote (17,5 s contra 9,6 s no DSQL, perto do limite de ~30 s do HTTP API); o lançamento avulso (444 ms contra 162 ms) fica como está.

## O que construir

`cartoes.protegida` lê todas as faturas dos 2 titulares em cada ação do lote (~157 ms por ação no DSQL). No caminho do lote (`backend/app/lote.py`), conferir só os titulares tocados pela gravação. Se não bastar, conferir só as faturas fechadas. O lançamento avulso não muda.

## Checklist

- [x] Teste que fixa o comportamento: lote que toca fatura paga continua recusado (`backend/tests/test_fatura_paga.py` segue verde)
- [x] Conferir só os titulares tocados no lote
- [x] Medir de novo com `DSQL_TESTE=1 uv run python medir_fatura_paga.py` (HITL: precisa de acesso ao DSQL); meta: lote de 50 bem abaixo dos 17,5 s

Falta só a medição no DSQL (HITL). Implementado: `cartoes.protegida(..., tocados=)` e `lote._titulares_tocados` nas ações de lançamento; antecipar parcelas segue conferindo todos.

Fora do escopo desta entrega (seguem conferindo todos os titulares, no lote): `antecipar_parcelas`, `criar_parcelamento`, `criar_recorrencia`, `alterar_recorrencia`. Estender `tocados` a eles só se a medição mostrar que ainda pesa. A fatura seguinte (`_garantir_a_seguinte`) agora só nasce para os titulares tocados pela ação do lote.

## Medição no DSQL (dono, 08/11, 11000 lançamentos de cartão, 190 faturas, 2 titulares)

| operação | com proteção | sem | custo |
|---|---|---|---|
| leitura de todas as faturas | 156 ms | — | — |
| lançamento | 454 ms | 184 ms | 270 ms |
| lote de 50 ações | 16140 ms | 6186 ms | 9955 ms |
| correção do longo | 1645 ms | 1505 ms | 139 ms |

**Meta não atingida**: o lote de 50 passou de 17456 ms (ticket 130) para 16140 ms, quase igual; o custo da proteção por ação (~199 ms) não caiu. O filtro por titular tocado não bastou: a leitura das faturas do titular continua cara (há o `antes` e o `depois`, e `faturas_do_titular` corre desde a fatura mais antiga porque o saldo anterior vem da anterior paga). A correção do longo (antes não medida) custa só 139 ms.

Próximo passo (decisão do dono): o ticket previa "conferir só as faturas fechadas", mas quase todas as 190 faturas são passadas e pagas, então isso pouparia pouco. A saída mais promissora é ler só as faturas dos meses que a ação toca, ou só o resumo (situação, datas, compras e pago) delas, sem refazer a conta desde 2019. Vale um ticket novo se o dono quiser seguir.
