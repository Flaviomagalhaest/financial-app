# Estorno avulso: crédito na fatura sem compra ligada

Type: task
Status: ready-for-agent
Blocked by: 133
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #323
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

O casal lança, na tela da fatura, um crédito que aparece na fatura sem compra identificável (correção de centavos, crédito de loja), um por um.

## Checklist

- [ ] Na tela da fatura, "Lançar crédito" ao lado de "Ajustar fatura": descrição, valor, data (a da linha na fatura), categoria, tags e pessoa opcionais
- [ ] Cai na fatura aberta ou fechada, nunca na paga; sem o limite do valor de compra
- [ ] Diminui fatura e mês; com categoria, também categoria, tag e item do planejamento; sem categoria, conta só no total do mês
- [ ] Aparece como crédito nas listas e na planilha; entra na fila sem internet como um lançamento
- [ ] Migração e versão nova do backup, se o modelo pedir uma marca de crédito sem `estorno_de`
- [ ] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q15, Q25 e Q26 do ticket 94; glossário **Estorno avulso**; adendo da ADR 0016.
