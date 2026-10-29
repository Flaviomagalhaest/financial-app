# Importador do Mobills: cruzamento e planilha de revisão

Type: task
Status: resolved
Blocked by: 65
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #121
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 164, 165, 166, 167, 168, 169, 170, 175

## O que construir

O dono roda localmente o importador sobre os exports do Mobills e recebe a planilha de revisão ([ADR 0007](../../../docs/adr/0007-historico-do-mobills-cruzado-e-sem-saldo.md), [ticket 18](18-importacao-do-mobills-cartao-e-datas.md)). Dados reais nunca entram no repositório nem no CI: só arquivos fictícios.

## Checklist

- [x] Lê o XLSX geral e as faturas por cartão e mês; cruza (esperado ~97,7% de casamento) e grava cada compra de cartão uma vez, com a data real, o cartão da fatura, as tags, a parcela e a situação do geral (o resultado fica em memória, na `Importacao`; gravar no banco é do [ticket 91](91-importador-do-mobills-gravar-e-refazer.md), e a taxa real é conferida no [ticket 92](92-rodar-o-importador-nos-exports-reais.md))
- [x] Planilha de revisão com de-para de categorias e tags (contagem e papel proposto), pares prováveis, grupos ambíguos, sequências de parcela quebradas e parcelamentos sem cartão; abas Conferência (mês a mês, com coluna para os totais do Mobills) e Faturas
- [x] Cadastro prévio da conta e dos 7 cartões ligando cada pasta de fatura (5 inativos ficam arquivados); tudo entra como conjunto e com autoria "importado do Mobills" (abas Conta e Cartões; gravar o cadastro e a autoria vai para o ticket 91)
- [x] A autoria "importado do Mobills" é `fonte = 'mobills'` no lançamento (coluna criada no ticket 41; `NULL` é "app"), sem pessoa; o menu ⋯ > Informações já a mostra (no `Lancamento` em memória; a gravação é do ticket 91)
- [ ] → [ticket 91](91-importador-do-mobills-gravar-e-refazer.md): O importador grava tudo com um único `criado_por`: o "Parece repetido" (ticket 41) só compara lançamentos de `criado_por` diferentes, e a importação não pode disparar avisos em massa
- [ ] → [ticket 91](91-importador-do-mobills-gravar-e-refazer.md): Refazer a importação apaga só o que tem essa autoria
- [x] Testes com XLSX fictícios cobrindo o cruzamento e a Conferência
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

Escopo dividido com o dono: quando o ticket começou, o esquema não tinha cartões, faturas, pessoa nem fonte (tickets 37 e 41). Por isso o 67 entrega a leitura, o cruzamento e a planilha de revisão, e o resultado fica em memória. Gravar no banco e refazer a importação ficaram no [ticket 91](91-importador-do-mobills-gravar-e-refazer.md). O 37 e o 41 chegaram à `main` antes do fim, e o cadastro da planilha já bate com as tabelas `cartoes` e `faturas` (dias opcionais, `arquivado_em`, fatura sem datas).

- **Código**: `backend/app/mobills/`, rodado com `uv run python -m app.mobills <geral> <faturas> <planilha.xlsx>`, como está no README. A entrada `importar` devolve a `Importacao`: conta, cartões, lançamentos com `fonte = "mobills"`, parcelamentos, ajustes de fatura e os impedimentos que ainda bloqueiam a gravação.
- **Cruzamento**: segue o `## Answer` do [ticket 18](18-importacao-do-mobills-cartao-e-datas.md). Primeiro o casamento exato, depois sem a categoria (vale a do geral, listado na aba Categoria diferente) e por fim o par provável (o dono decide `juntar` ou `separar`). Dentro de um grupo, a ordem é pela data da compra, de qualquer cartão. Quando as linhas do geral têm tags ou situação diferentes, o grupo vai para a aba Grupos ambíguos.
- **Já aqui, adiantando o ticket 68**: o `Reajuste de fatura` sai dos lançamentos e vira o ajuste da fatura dele (a Conferência e as Faturas precisam dele); as parcelas são reagrupadas para as abas Parcelas quebradas e Parcelamentos sem cartão; e a parcela do geral que ainda não tem fatura herda o cartão e a data da compra do parcelamento. Gerar as parcelas que faltam, a regra dos pendentes e o backup continuam no 68.
- **Planilha**: cada rodada a reescreve e mantém o que o dono editou, incluindo a coluna Mobills da Conferência e das Faturas, que dá a diferença na rodada seguinte. A Conferência vai até o último mês com lançamento pago.
- **Pendências**: [ticket 91](91-importador-do-mobills-gravar-e-refazer.md) (gravar, `criado_por` único, refazer e a pergunta ao dono sobre o ADR 0012) e [ticket 92](92-rodar-o-importador-nos-exports-reais.md) (rodar nos exports reais: taxa de casamento, separador das tags, layout das pastas e se Grupos ambíguos e Parcelas quebradas precisam de decisão). O [ticket 69](69-virada-para-o-app.md) passa a ser bloqueado por eles.
