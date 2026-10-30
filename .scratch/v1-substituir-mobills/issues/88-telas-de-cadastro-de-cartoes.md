# Telas de cadastro de cartões e das datas da fatura

Type: task
Status: resolved
Blocked by: 37
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #164
Origem: [ticket 37](37-cartoes-e-faturas.md): a API de cartões e faturas existe (`/api/cartoes`, `GET /api/cartoes/{id}/faturas`, `PATCH /api/cartoes/{id}/faturas/{mes}`), mas nenhuma tela cadastra cartão nem acerta as datas de uma fatura; nenhum outro ticket cobre essas telas (o [55](55-aba-cartoes.md) é a aba de consulta e o [42](42-jornada-completa-do-lancamento-rapido.md), a fileira do lançamento)

## O que construir

Na configuração, junto das contas (`#/contas-e-categorias`, ticket 74), o casal cadastra, edita e arquiva cartões e acerta o fechamento e o vencimento de uma fatura, só com internet ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)).

## Checklist

- [x] Cartão titular: nome, dia de fechamento e de vencimento padrão, limite opcional e "conta no mês anterior ao fechamento"; cartão adicional ligado a um titular (sem dias nem limite próprios); arquivar e desarquivar
- [x] Mudar o dia padrão avisa que só as faturas abertas e futuras mudam e que as compras delas vão para a fatura certa
- [x] Acertar o fechamento e o vencimento de uma fatura (a atual, a próxima ou outra pelo mês), com o aviso de que as compras se redistribuem
- [x] Botões desativados com "precisa de internet" sem rede (história 53)
- [x] Testes de navegador
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- As telas são a seção "Cartões" de `#/contas-e-categorias` (`web/src/contas-e-categorias/SecaoDeCartoes.tsx`), dentro do mesmo `fieldset` das contas, que já desativa tudo sem rede com o aviso "Mudar contas e categorias precisa de internet." (coberto em `sem-internet.spec.ts`).
- Cartão adicional escolhe o titular no cadastro e não tem campos de dia nem de limite; o titular de um cartão não muda depois (a API recusa). Arquivados aparecem com "(arquivado)" e voltam com "Desarquivar" (`useCartoesComArquivados`, que também recarrega a lista dos ativos).
- "Acertar fatura de <cartão>" lista as faturas que já nasceram (abre na aberta mais antiga) e "Outro mês…" para uma que ainda vai nascer; só aparece para titular não arquivado. O aviso de redistribuição das compras está no formulário, e o do dia padrão no formulário de edição.
- `emCentavos` saiu da tela de contas para `web/src/lancamentos/dinheiro.ts`, porque as duas telas usam.
- Testes de navegador: `web/e2e/cartoes-cadastro.spec.ts`.
