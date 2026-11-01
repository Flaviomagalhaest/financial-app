# Alcance da mudança na parcela: só esta, esta e as próximas, todas

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Opus
Effort recomendado: high
Issue: #324
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

Ao mudar qualquer campo de uma parcela, o app pergunta "Só esta", "Esta e as próximas" ou "Todas (inclusive as já realizadas)". Hoje descrição, categorias, tags, pessoa e item vão sempre para todas, e só valor, data, conta e fatura se alteram à mão.

## Checklist

- [ ] API: a edição de parcela recebe o alcance, para qualquer campo
- [ ] "Só esta" marca a parcela alterada à mão naquele campo
- [ ] "Esta e as próximas" e "Todas" preservam os campos alterados à mão das outras parcelas e respondem quantas ficaram como estavam; a tela mostra o aviso
- [ ] A realizada que muda passa pela confirmação que a correção do parcelamento já pede
- [ ] Fila sem internet: o alcance vai junto do pedido (ou a escolha exige internet, decidir na implementação e registrar)
- [ ] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q39 e Q40 do ticket 94; glossário **Alcance da mudança na parcela** e **Parcela alterada à mão**.
