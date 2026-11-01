# Sugestão no aparelho até o índice ser buscado de novo

Type: task
Status: resolved
Blocked by: —
Skills: `triage`; depois `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #192
Origem: revisão do [ticket 63](63-sugestao-pelo-historico.md): o `useSugestao` (`web/src/dados/index.ts`) põe por cima do índice guardado os lançamentos que ele ainda não tem, e isso tem imprecisões até o índice ser buscado de novo (logo depois do próximo envio da fila com internet)

## O que construir

Decidir na triagem se alguma destas imprecisões vale o código que custa e, se valer, corrigir:

- **Mudar só o valor põe a sugestão primeiro no aparelho.** O servidor só conta mudanças na descrição, no tipo, na conta, nas categorias, nas tags e na pessoa. O aparelho só sabe quando o lançamento enviado mudou (`alterado_em`), não o quê, e o não enviado usa `feitoEm`. Para o não enviado, a `base` da fila diria se esses campos mudaram.
- **A sugestão antiga de um lançamento corrigido ou excluído sem internet continua.** O índice não diz de quais lançamentos cada sugestão veio, então o aparelho não sabe que ela só existia por causa daquele lançamento. Ela fica atrás da nova e some quando o índice é buscado de novo.
- **Normalização fora do alfabeto latino.** A `chave` do servidor (`app/sugestao.py`) e a `chaveDaDescricao` do aparelho (`web/src/dados/sugestao.ts`) são iguais para português. Elas diferem em dígitos de outras escritas (`\d` no Python pega dígitos Unicode) e em marcas que ocupam espaço próprio (`unicodedata.combining` contra `\p{M}`).

## Checklist

- [x] Triagem: o que corrigir e o que fica como está (anotar aqui)
  - **Mudar só o valor**: fica como está. Só põe a sugestão primeiro até o índice ser buscado de novo, e corrigir exigiria o aparelho saber o que mudou no enviado, o que o contrato não traz.
  - **Sugestão antiga de lançamento corrigido/excluído offline**: fica como está. Exigiria o índice dizer de quais lançamentos veio cada sugestão (mudança de contrato e de tamanho); ela fica atrás da nova e some na próxima busca.
  - **Normalização**: corrigido o dígito (`\d` do Python agora é ASCII, como o do aparelho). As marcas (`combining` contra `\p{M}`) só diferem em escritas fora do português e ficam como estão.
- [x] O que for corrigido, com teste de navegador (`web/e2e/sugestao.spec.ts`) ou de API (`backend/tests/test_sugestao.py`): `test_chave_so_tira_parcela_com_digitos_ascii`
- [ ] Verificações do projeto rodando e PR aberto para `main`
