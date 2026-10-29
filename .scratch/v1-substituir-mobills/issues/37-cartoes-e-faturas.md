# Cartões e faturas

Type: task
Status: resolved
Blocked by: 36
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #91
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 69, 70, 71, 72, 73, 74, 75, 76, 86

## O que construir

O casal cadastra cartões e cada compra cai na fatura certa pelo fechamento e conta no mês da fatura ([ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md)).

## Checklist

- [x] Cartões com dia de fechamento e vencimento padrão, limite opcional, regra "mês anterior ao fechamento", cartão adicional ligado ao titular (compras na fatura do titular) e arquivar
- [x] Fatura por cartão por mês, criada quando a primeira compra precisa dela, com fechamento e vencimento editáveis; compra no próprio dia do fechamento vai para a seguinte; troca manual de fatura
- [x] Mudar o dia padrão redistribui só faturas abertas e futuras; fatura fechada nunca muda
- [x] O lançamento grava o mês em que conta (mês da fatura no cartão, a data no resto), com índice por esse mês
- [x] Teste com o exemplo do glossário: compra de 28/03 em fatura que fecha em 25/04 conta em abril
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Modelo: [ADR 0015](../../../docs/adr/0015-compra-no-cartao-guarda-o-cartao-e-o-mes-no-lancamento.md). A compra no cartão é um lançamento com o cartão em `conta_id` (o DSQL não tira o `NOT NULL` da coluna); a fatura é a linha de `faturas` com chave `(cartao_id do titular, mes)`, e o lançamento grava `mes` (o mês em que conta) e `fatura_a_mao`. Migrations `0018` a `0023`; o índice `lancamentos_por_mes` é `CREATE INDEX ASYNC`, e `aplicar_migrations` tira o `ASYNC` fora do DSQL. A `0022` preenche o `mes` dos lançamentos antigos pela data.
- API: `POST/GET /api/cartoes` (`?arquivados=true`), `PUT /api/cartoes/{id}` (editar, arquivar; o titular de um cartão não muda), `GET /api/cartoes/{id}/faturas` e `PATCH /api/cartoes/{id}/faturas/{mes}` (a fatura que ainda não nasceu nasce aqui). O lançamento ganhou `mes` na resposta e `fatura_mes` (resposta, criação e edição; mandar é a troca à mão; numa conta, 422 "fatura só em compra no cartão"). `fatura_mes` é um campo da versão por campo (ADR 0011): a redistribuição sobe a versão com a `origem` "datas do cartão <nome>", e a tela de conflito do app mostra "Fatura".
- Escolha da fatura (`app/faturas.py`): a primeira fatura que fecha depois da data da compra, contando com o fechamento editado das que já existem; começa pela do mês anterior, porque um fechamento pode escorregar para o mês da compra. Editar a data ou trocar a conta/cartão escolhe de novo, salvo a troca à mão (que só trocar de cartão desfaz); editar outros campos não mexe na fatura.
- Confirmar um previsto no cartão com outra data também escolhe a fatura de novo.
- Recusas (422): troca à mão para uma fatura que fechou antes da compra; fechamento editado que não fica entre o da fatura anterior e o da seguinte (a escolha da fatura conta com fechamentos em ordem); vencimento antes do fechamento; compra nova em cartão arquivado ou no adicional de um titular arquivado; adicional com dias, regra ou limite próprios, ou de outro adicional.
- A migration `0022` preenche no máximo 3.000 lançamentos antigos (o limite da transação no DSQL; `prod` ainda não tem lançamentos antes da virada); o que sobrar, e o que a API antiga gravar durante o deploy, fica com `mes` vazio, que a leitura cobre pela data (`COALESCE`).
- Backup na versão 8, com o conversor da 7 (`cartoes` e `faturas` vazias, `mes` pela data). A guarda da planilha (`ler_lancamentos`) passou a esperar a coluna `pessoa` do [ticket 41](41-pessoa-autoria-e-parece-repetido.md): com cartões e faturas, todas as tabelas de `TABELAS_DA_PLANILHA` já existiam e a exportação da planilha daria 500. O 41 faz o [77](77-ligar-o-csv-de-planilha-ao-esquema-real.md) junto.
- Comportamentos provisórios (dia padrão sobre datas editadas, fatura fechada que recebe compra esquecida, etc.) para o dono conferir no [ticket 85](85-conferir-as-regras-de-fatura.md).
- Fora deste ticket, de propósito: as telas de cadastro de cartão e de datas da fatura ([ticket 84](84-telas-de-cadastro-de-cartoes.md)); a fileira "conta ou cartão" do lançamento ([42](42-jornada-completa-do-lancamento-rapido.md)); a situação "paga" da fatura ([38](38-pagamento-de-fatura.md)); a aba Cartões ([55](55-aba-cartoes.md)).
- Os testes de navegador tiveram uma falha intermitente sem relação com este ticket: [ticket 86](86-teste-do-recusado-intermitente.md).
