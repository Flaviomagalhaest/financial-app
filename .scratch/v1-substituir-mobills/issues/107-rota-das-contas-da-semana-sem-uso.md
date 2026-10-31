# Rota das contas da semana sem uso no app

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #216
Origem: [ticket 83](83-confirmar-previsto-sem-internet-pela-fila.md) (depois do merge com o [ticket 53](53-aba-hoje.md), o bloco "Contas da semana" lê `contas_da_semana` de `GET /api/hoje`, e nenhuma tela chama mais `GET /api/contas-da-semana`)

## O que construir

Tirar a rota `GET /api/contas-da-semana` (`contas_da_semana` em `backend/app/lancamentos.py`), que repete `contas_da_semana_de_hoje` e ficou sem uso no app, ou dizer no README por que ela fica.

## Checklist

- [x] Os testes de `backend/tests/test_previstos.py` que leem a rota passam a ler `contas_da_semana` de `GET /api/hoje` (ou a função `contas_da_semana_de_hoje`), sem perder o que eles cobrem: ordem, janela de `contasDaSemanaDias`, atrasados, automático de fora, confirmado sai
- [x] Rota e modelo `ContasDaSemana` removidos; `openapi.json` e `web/src/api/schema.d.ts` regenerados; README sem a rota
- [x] Verificações do projeto rodando e PR aberto para `main`
