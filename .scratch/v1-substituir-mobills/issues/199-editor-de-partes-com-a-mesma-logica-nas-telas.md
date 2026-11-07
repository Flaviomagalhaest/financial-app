# Editor de partes com a mesma lógica nas telas de lançamento e do parcelamento

Type: task
Status: claimed
Blocked by: —
Skills: `codebase-design`, `implement`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #487
Origem: [ticket 158](158-mudar-as-partes-pela-tela-do-parcelamento.md): revisão de padrões

## O que construir

A tela do parcelamento (`web/src/lancamentos/TelaDoParcelamento.tsx`) repete a lógica de partes da tela de lançamento (`TelaDeLancamento.tsx`): dividir (a 1ª parte com a classificação da compra e uma vazia), juntar (a compra volta com a classificação e o nome da parte que ficou), soltar a proporção quando um valor ou o número de partes muda e redividir as partes pela proporção quando o valor muda. Levar essas regras para `web/src/lancamentos/partes.tsx`, ao lado de `parteNova` e `emEdicao`, e usá-las nas duas telas (e na da recorrência, se couber), talvez com um tipo para a classificação (categorias, tags e pessoa) que viaja junta.

## Checklist

- [ ] As regras de dividir, juntar e seguir a proporção num lugar só, usado pelas telas
- [ ] Specs de partes (`partes-da-compra`, `partes-na-compra-parcelada`, `partes-pela-tela-do-parcelamento`, `partes-na-recorrencia`) verdes; verificações do projeto e PR para `main`
