# Como o app roda na AWS

Type: grilling
Status: open
Blocked by: 08, 09
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono); apoio: `research` se surgir fato a confirmar
Modelo recomendado: Opus
Effort recomendado: high
Issue: #30
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Qual arquitetura na AWS cumpre o custo-alvo do mapa?

Cobrir: login (como os dois entram e continuam logados); API em Python (Lambda com API Gateway ou URL de função); hospedagem do app; contrato entre o app e a API (o app não é em Python); infraestrutura como código (CDK, SAM ou Terraform); ambientes (só produção ou também desenvolvimento); backup e restauração; alerta de orçamento; configuração da conta filha da organização.

## Checklist

- [ ] Decisão registrada em `## Answer`
- [ ] ADR em `docs/adr/` para as escolhas com lock-in

## Comments

- O [ticket 09](09-banco-de-dados-e-regiao.md) decidiu ([ADR 0007](../../../docs/adr/0007-aurora-dsql-em-sao-paulo.md)): Aurora DSQL em sa-east-1, com o app inteiro nessa região (API, bucket do backup, hospedagem, login); em us-east-1 só os serviços globais (IAM, Budgets, certificado do CloudFront). Todo serviço escolhido aqui precisa existir em sa-east-1. O backup é uma tarefa agendada diária que grava a exportação completa num S3 com versões, 90 dias e Object Lock; região e endpoint só em configuração; autenticação no DSQL só por IAM (a API usa uma role, nunca chave de usuário).
- Configuração da conta filha: a SCP `p-q0eemrzp` (`AdvancedModeRegionRestrictionSecurityControlPolicy`, na raiz da organização) teve `sa-east-1` acrescentado ao bloco `RegionFloor` em 2026-10-25. A origem dela é desconhecida (pode ser um assistente que a reaplica sem São Paulo) e ela tem 5.094 dos 5.120 caracteres permitidos: liberar mais serviços ou regiões exige dividi-la. Decidir aqui se ela vira infraestrutura como código ou fica registrada à mão.
- O usuário IAM `financial-cli` (chave de acesso de longa duração) foi criado para testes a partir da máquina do dono; desativar a chave quando os testes do [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md) acabarem.
