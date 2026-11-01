# Estorno avulso: crédito na fatura sem compra ligada

Type: task
Status: resolved
Blocked by: 133
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #323
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

O casal lança, na tela da fatura, um crédito que aparece na fatura sem compra identificável (correção de centavos, crédito de loja), um por um.

## Checklist

- [x] Na tela da fatura, "Lançar crédito" ao lado de "Ajustar fatura": descrição, valor, data (a da linha na fatura), categoria, tags e pessoa opcionais
- [x] Cai na fatura aberta ou fechada, nunca na paga; sem o limite do valor de compra
- [x] Diminui fatura e mês; com categoria, também categoria, tag e item do planejamento; sem categoria, conta só no total do mês
- [x] Aparece como crédito nas listas e na planilha; entra na fila sem internet como um lançamento
- [x] Migração e versão nova do backup, se o modelo pedir uma marca de crédito sem `estorno_de`
- [x] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q15, Q25 e Q26 do ticket 94; glossário **Estorno avulso**; adendo da ADR 0016.

## Como ficou

- Modelo: coluna `estorno_avulso` em `lancamentos` (migration `0060`), backup na versão 25 (conversor 24→25, esquema e importador do Mobills). Detalhes no adendo da [ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md).
- API: `POST /api/lancamentos` com `estorno_avulso: true` (e `categoria_ids` vazio, se quiser); a edição aceita tirar a categoria só dele. Testes em `backend/tests/test_estorno_e_ajuste.py`, `test_fatura_paga.py`, `test_exportacoes.py` e `test_restauracao.py`.
- App: "Lançar crédito" na tela da fatura (`#/credito/<cartão>`, a `TelaDeLancamento` em modo avulso); editar pelo Histórico. Teste de navegador em `web/e2e/estorno-avulso.spec.ts`, inclusive sem internet.

- Pendências da revisão: [ticket 149](149-estorno-avulso-pendencias.md).
