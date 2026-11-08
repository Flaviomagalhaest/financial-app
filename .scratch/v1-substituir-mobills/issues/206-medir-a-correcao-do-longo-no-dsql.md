# Medir a correção do parcelamento longo no DSQL

Type: task
Status: resolved
Blocked by: [203](203-simulacao-da-correcao-usa-savepoint-no-dsql.md)
Skills: `run`; HITL (precisa de acesso ao DSQL)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #537
Origem: [ticket 202](202-decidir-o-custo-da-protecao-no-dsql.md): a decisão foi tomada sem essa medida; a correção do longo ainda não foi medida no DSQL.

## Checklist

- [x] Rodar `DSQL_TESTE=1 uv run python medir_fatura_paga.py` depois do 203 e registrar aqui a correção do parcelamento longo, com e sem proteção
- [x] Se pesar, abrir ticket de implementação (mesma ideia do 205)

## Resultado (medido pelo dono num DSQL de teste)

11.000 lançamentos de cartão, 190 faturas, 2 titulares; ler todas as faturas: 361 ms. Parcelamento de 420 parcelas, 83 por lote.

| Operação | Com proteção | Sem | Custo |
|---|---|---|---|
| Lançamento | 475 ms | 199 ms | 276 ms |
| Lote de 50 ações | 17.165 ms | 7.643 ms | 9.521 ms |
| Correção do longo | 2.117 ms | 1.795 ms | 322 ms |

**Conclusão:** a correção do parcelamento longo não pesa: a proteção custa 322 ms sobre 1,8 s, e o total fica muito abaixo dos 29 s da Lambda da API. Não abre ticket de implementação. Observação fora do escopo deste ticket: o lote de 50 ações com proteção leva 17 s, perto do limite de 29 s da Lambda; ver se o ticket 202 já cobre isso.
