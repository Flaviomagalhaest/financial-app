# Tarefa diária para no parcelamento que um conserto recusa

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #363
Origem: [ticket 139](139-partes-na-compra-parcelada.md): revisão de spec

## O que construir

`parcelamentos.completar_todos` (a tarefa diária que termina a correção que parou no meio) não pega a recusa (`HTTPException`) de um parcelamento, ao contrário de `mudanca_na_parcela.terminar_as_mudancas_pendentes`. Se o refazer de um parcelamento passar a ser recusado depois do pedido (por exemplo, a fatura de uma parcela foi paga no meio, ou uma parcela com partes próprias ficaria sem um centavo numa parte), a tarefa para ali todo dia e não chega aos outros consertos, à realização dos automáticos nem ao cancelamento dos lotes parados. O 139 confere a divisão das partes antes de gravar a correção, mas a recusa no meio do refazer continua possível por outros caminhos.

## Checklist

- [ ] `completar_todos` segue para os outros parcelamentos quando um é recusado, e o recusado sai do pendente (como `_desistir`) ou fica registrado
- [ ] A tarefa diária chega aos passos seguintes mesmo com um parcelamento recusado
- [ ] Teste de API; verificações do projeto e PR para `main`
