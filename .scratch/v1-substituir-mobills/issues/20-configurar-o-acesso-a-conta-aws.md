# Configurar o acesso à conta AWS

Type: task
Status: resolved
Blocked by: 17
Skills: nenhuma de tipo; tarefa HITL (o dono faz no console e no CLI da AWS); apoio: `wizard` para guiar os passos
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #59
Origem: decisões de conta de [Como o app roda na AWS](12-como-o-app-roda-na-aws.md) ([ADR 0010](../../../docs/adr/0010-app-na-aws-cloudfront-http-api-e-uma-lambda.md)); lacunas da pesquisa na branch `research/aws-arquitetura`

## Question

A conta filha 255235818791 está pronta para o app: acesso humano só com MFA, nenhuma chave de longa duração, a SCP registrada no repositório e os pontos que a documentação da AWS deixou ambíguos conferidos?

Bloqueado pelo [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md) porque os testes dele usam a chave de acesso do `financial-cli`. Os itens que não dependem da chave (MFA, SCP, cota) podem ser feitos antes.

## Checklist

- [x] Root da conta 255235818791 com MFA, guardado e sem uso no dia a dia
- [x] Usuário IAM `financial-cli` com MFA obrigatório (é o acesso humano do dono na conta); senha de console só se o dono quiser entrar no console com ele
- [x] Chave de acesso de longa duração do `financial-cli` desativada depois do ticket 17; o CLI na máquina do dono passa a usar credencial temporária com MFA, e o deploy sai só pelo GitHub Actions com OIDC
- [x] Cópia do JSON atual da SCP `p-q0eemrzp` em `docs/aws/` (`aws organizations describe-policy --policy-id p-q0eemrzp`, da conta de gerência), com uma nota de que ela libera sa-east-1 no bloco `RegionFloor` e de que reaplicá-la sem São Paulo derruba o app
- [x] Cota de execuções simultâneas do Lambda em sa-east-1 conferida no Service Quotas (a documentação dá 1.000 como padrão; conta nova pode ter menos)
- [ ] (passou para o [ticket 64](64-backup-diario.md), porque o bucket ainda não existe) Confirmar que uma regra de ciclo de vida apaga as versões do bucket de backup depois que os 90 dias do Object Lock em compliance vencem (a documentação é ambígua); senão, o bucket cresce sem fim, ainda que em centavos
- [x] Resultado em `## Answer`

## Answer

Sim, com uma conferência que fica para o ticket 64. O dono rodou `scripts/configurar-conta-aws.sh` em 2026-10-28:

- Root com MFA, guardado e sem chave de acesso; `financial-cli` com MFA obrigatório por política; chave de acesso do `financial-cli` desativada (ticket 17 resolvido). O CLI usa credencial temporária com MFA e o deploy sai pelo GitHub Actions com OIDC. Confirmado pelo dono: MFA configurado no root e no `financial-cli`, e a chave de acesso do `financial-cli` foi excluída (não só desativada).
- SCP `p-q0eemrzp` copiada para [`docs/aws/scp-p-q0eemrzp.json`](../../../docs/aws/scp-p-q0eemrzp.json), com o aviso de que reaplicá-la sem `sa-east-1` derruba o app em [`docs/aws/README.md`](../../../docs/aws/README.md). O `RegionFloor` libera `us-east-1`, `us-east-2`, `us-west-2` e `sa-east-1`.
- Cota de execuções simultâneas do Lambda em sa-east-1: 1.000, o padrão da documentação.
- Regra de ciclo de vida do bucket de backup: o bucket ainda não existe, então a conferência passou para o [ticket 64](64-backup-diario.md), que cria o bucket.

## Comments

- 2026-10-28: o ticket 17 está resolvido, então o bloqueio acabou. Preparei `scripts/configurar-conta-aws.sh` (skill `wizard`), que guia as seis etapas do checklist e grava a cópia da SCP em `docs/aws/scp-p-q0eemrzp.json` quando a CLI tem acesso à conta de gerência. Falta o dono rodá-lo (`scripts/configurar-conta-aws.sh`) e preencher `## Answer`. O bucket de backup ainda não existe, então a conferência da regra de ciclo de vida pode ficar para a infraestrutura dele.
