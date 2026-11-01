# Partes da compra à vista

Type: task
Status: ready-for-agent
Blocked by: 133
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Opus
Effort recomendado: high
Issue: #325
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

Uma despesa à vista, no cartão ou na conta, pode ser dividida em partes, cada uma com descrição, valor, categorias, tags, pessoa e item próprios ([ADR 0022](../../../docs/adr/0022-partes-da-compra.md)).

## Checklist

- [ ] Modelo e migração: partes ligadas ao lançamento; versão nova do backup
- [ ] API: criar e editar compra com 2 partes ou mais, soma igual ao valor (senão 422); tirar a penúltima parte devolve os dados dela à compra
- [ ] A compra com partes não tem categoria, tag nem pessoa próprias
- [ ] Somas: categoria, tag, pessoa e item do planejamento leem as partes; fatura, mês e saldo leem a compra
- [ ] Telas: dividir em partes no lançamento; a compra aparece numa linha só na fatura e no extrato e abre as partes; o filtro por categoria, tag ou pessoa mostra só a parte que bate, com o valor dela
- [ ] Aviso de planejamento na tela de lançar: uma linha por parte
- [ ] Planilha: uma linha por parte ("<compra> — <parte>")
- [ ] Fila sem internet: a compra com partes é um pedido só; no conflito, as partes são um campo só
- [ ] A importação do Mobills não cria partes
- [ ] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q16, Q17, Q27 a Q29, Q31, Q32, Q44 e Q46 do ticket 94.
