# Importador do Mobills: cruzamento e planilha de revisão

Type: task
Status: claimed
Blocked by: 65
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #121
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 164, 165, 166, 167, 168, 169, 170, 175

## O que construir

O dono roda localmente o importador sobre os exports do Mobills e recebe a planilha de revisão ([ADR 0007](../../../docs/adr/0007-historico-do-mobills-cruzado-e-sem-saldo.md), [ticket 18](18-importacao-do-mobills-cartao-e-datas.md)). Dados reais nunca entram no repositório nem no CI: só arquivos fictícios.

## Checklist

- [ ] Lê o XLSX geral e as faturas por cartão e mês; cruza (esperado ~97,7% de casamento) e grava cada compra de cartão uma vez, com a data real, o cartão da fatura, as tags, a parcela e a situação do geral
- [ ] Planilha de revisão com de-para de categorias e tags (contagem e papel proposto), pares prováveis, grupos ambíguos, sequências de parcela quebradas e parcelamentos sem cartão; abas Conferência (mês a mês, com coluna para os totais do Mobills) e Faturas
- [ ] Cadastro prévio da conta e dos 7 cartões ligando cada pasta de fatura (5 inativos ficam arquivados); tudo entra como conjunto e com autoria "importado do Mobills"
- [ ] Refazer a importação apaga só o que tem essa autoria
- [ ] Testes com XLSX fictícios cobrindo o cruzamento e a Conferência
- [ ] Verificações do projeto rodando e PR aberto para `main`
