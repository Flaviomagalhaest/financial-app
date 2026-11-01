# Alcance da mudança na parcela: só esta, esta e as próximas, todas

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Opus
Effort recomendado: high
Issue: #324
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

Ao mudar qualquer campo de uma parcela, o app pergunta "Só esta", "Esta e as próximas" ou "Todas (inclusive as já realizadas)". Hoje descrição, categorias, tags, pessoa e item vão sempre para todas, e só valor, data, conta e fatura se alteram à mão.

## Checklist

- [x] API: a edição de parcela recebe o alcance, para qualquer campo
- [x] "Só esta" marca a parcela alterada à mão naquele campo
- [x] "Esta e as próximas" e "Todas" preservam os campos alterados à mão das outras parcelas e respondem quantas ficaram como estavam; a tela mostra o aviso
- [x] A realizada que muda passa pela confirmação que a correção do parcelamento já pede
- [x] Fila sem internet: o alcance vai junto do pedido (ou a escolha exige internet, decidir na implementação e registrar)
- [x] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q39 e Q40 do ticket 94; glossário **Alcance da mudança na parcela** e **Parcela alterada à mão**.

## Answer

Feito ([ADR 0023](../../../docs/adr/0023-alcance-da-mudanca-na-parcela.md)):

- **API**: `PATCH /api/parcelas/{id}` recebe a edição da parcela com `alcance` (`so_esta`, `esta_e_as_proximas`, `todas`) e `confirmar_realizadas`, e responde a parcela e `parcelas_mantidas`.
  - A classificação (descrição, categorias, tags, pessoa, item) vai para o parcelamento, a partir da parcela mudada ou desde a 1ª.
  - Em "todas", o valor e a data viram a correção do valor da parcela e da data.
  - O valor e a data daqui para frente, a conta e a fatura vão parcela a parcela, à mão em cada uma.
- **Alterado à mão por campo**: "só esta" é a edição comum e marca o campo. A correção do parcelamento e os dois outros alcances preservam o campo marcado nas outras parcelas e dizem quantas ficaram (`parcelas_mantidas`, também na resposta da correção). A edição em lote não marca a parcela, e a migration 0059 tira a marca que o lote antigo deixou.
- **Realizadas**: a que não é a parcela mudada e muda de valor, data, conta ou fatura passa pela confirmação da correção (409 com o aviso).
- **Sem internet**: "só esta" vai pela fila; "esta e as próximas" e "todas" pedem internet (os botões ficam desativados sem rede), como a correção do parcelamento.
- **Telas**: ao salvar uma parcela que mudou, a tela pergunta o alcance, mostra o aviso das realizadas e o de quantas ficaram como estavam. A tela do parcelamento também mostra esse aviso.
- **Pendências**: [144](144-valor-e-data-daqui-para-frente-no-parcelamento.md) (decisão do dono: trecho no parcelamento e conta nova) e [145](145-retomar-a-mudanca-parcela-a-parcela.md) (retomar a mudança parcela a parcela que parou no meio). O [146](146-escopo-na-parcela-e-a-classificacao-editada-a-mao.md) leva ao dono o conflito com a Q7 do ticket 99 ([142](142-escopo-na-edicao-de-parcela-e-aviso-ao-excluir.md)), que pede a classificação valendo também na parcela editada à mão.
