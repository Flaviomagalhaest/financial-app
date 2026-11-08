# Busca abre o Parcelamento e a Recorrência de um lançamento previsto

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`, `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #560
Origem: [ticket 207](207-historico-abre-com-previstos-distantes.md): sem os previstos futuros no Histórico, o parcelamento e o previsto avulso só são alcançáveis pela Busca, que tem Editar mas não o ⋯ com Parcelamento e Recorrência.

## Problema

Hoje a tela do Parcelamento abre pelo ⋯ da linha do Histórico (`#/parcelamento/<id>`). A Busca (`TelaDaBusca.tsx`) só oferece `Editar`. A recorrência ainda abre por Contas e categorias; o parcelamento não tem entrada própria.

## Checklist

- [ ] A linha da Busca ganha o caminho para Parcelamento e Recorrência quando o lançamento os tem (reaproveitar o `MenuDeAcoes`)
- [ ] Spec: da Busca de um previsto de parcelamento até a tela do Parcelamento
- [ ] Specs e verificações verdes; PR para `main`
