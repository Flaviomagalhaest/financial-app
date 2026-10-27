# Exportação

Type: grilling
Status: open
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #73
Origem: fog "Exportação" do [mapa V1 que substitui o Mobills](../map.md), graduado agora que o banco ([ticket 09](09-banco-de-dados-e-regiao.md)), a arquitetura na AWS ([ticket 12](12-como-o-app-roda-na-aws.md)) e a importação do histórico ([ticket 18](18-importacao-do-mobills-cartao-e-datas.md)) estão decididos

## Question

Qual o formato e o conteúdo da exportação completa do app, que também é o backup diário e precisa poder ser importada de volta num banco novo?

Pontos a decidir:

- o formato do backup (por exemplo, um arquivo só com todas as tabelas ou um arquivo por tabela) e o do CSV para o casal abrir numa planilha, e se são o mesmo arquivo ou dois;
- o que entra: lançamentos com categorias, tags, pessoa e quem criou e alterou por último, contas, cartões, faturas, regras de recorrência e parcelamento, planejamento, favoritos, filtros salvos, e o que fica de fora (usuários e senhas do Cognito);
- como a importação refaz o banco do zero, sem duplicar e com a versão do formato, e como o teste de restauração do CI ([ADR 0010](../../../docs/adr/0010-app-na-aws-cloudfront-http-api-e-uma-lambda.md)) a usa;
- como o "exportar tudo" do app roda (no servidor, com o histórico de 7 anos) e entrega o arquivo ao aparelho;
- a relação com a importação do Mobills ([ADR 0007](../../../docs/adr/0007-historico-do-mobills-cruzado-e-sem-saldo.md)): se o formato do backup serve de formato de entrada para a mesma carga.

## Checklist

- [ ] Decisão registrada em `## Answer`
- [ ] Vocabulário novo no `GLOSSARY.md` e ADR para o que for difícil de reverter
- [ ] Linha em "Decisions so far" do mapa e item removido de "Not yet specified"
