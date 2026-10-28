# Conta AWS 255235818791

## SCP `p-q0eemrzp`

`scp-p-q0eemrzp.json` é a cópia da SCP `AdvancedModeRegionRestrictionSecurityControlPolicy`, na raiz da organização (obtida em 2026-10-28 com `aws organizations describe-policy --policy-id p-q0eemrzp --query Policy.Content`, na conta de gerência).

O bloco `RegionFloor` libera `sa-east-1` (São Paulo). **Reaplicar a SCP sem `sa-east-1` derruba o app**: o Aurora DSQL, a Lambda, o S3 do backup e o login ficam todos em São Paulo (ADR 0009 e 0010).

Ela fica fora da infraestrutura como código, porque o repositório do app não deve ter credencial da conta de gerência. Se ela mudar na AWS, atualize a cópia.
