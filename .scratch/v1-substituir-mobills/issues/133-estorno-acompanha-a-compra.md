# O estorno acompanha a compra e trava a exclusão

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #321
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

O estorno passa a seguir as categorias e tags da compra (também as arquivadas), e a compra com estorno não pode mais ser excluída. Hoje o estorno guarda uma cópia que não muda, recusa a tag arquivada e fica solto quando a compra sai.

## Checklist

- [ ] Estorno sem categorias e tags próprias: vale o que a compra tem agora; mudar a compra muda o que o estorno desconta (categoria, tag, item do planejamento)
- [ ] Estorno de compra com tag ou categoria arquivada é aceito
- [ ] Excluir compra com estorno: 422 "a compra tem estorno; exclua o estorno antes"
- [ ] Tela: "Excluir" segue ativo na compra com estorno; ao tocar, mostra a mensagem com link para o estorno
- [ ] "Estornar" aparece também na compra de cartão arquivado (cartão reemitido); a escolha do cartão segue só com os ativos
- [ ] Fila sem internet: a exclusão recusada aparece como recusada, com o motivo
- [ ] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q2, Q4, Q7, Q22 e Q24 do ticket 94; adendo da [ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md).
- Ponto de partida: `_conferir_estorno` em `backend/app/lancamentos.py`.
