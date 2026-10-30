# Tornar o repositório público

Status: ready-for-human
Blocked by: —
Skills: `wizard` (se quiser um roteiro guiado dos passos do dono); HITL: só o dono mexe nas configurações do repositório no GitHub
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #239
Origem: pedido do dono na sessão que investigou a cota de minutos do GitHub Actions (plano Free) esgotada: em repositório público os minutos dos runners padrão não contam. Decisão registrada na [ADR 0019](../../../docs/adr/0019-repositorio-publico-com-o-historico-mantido.md)

## Problema

O CI/CD parou porque a cota de minutos do Actions do plano Free acabou. O dono decidiu tornar o repositório público, mantendo o histórico. Antes de virar público, o número da conta AWS e o e-mail do dono saíram da árvore atual, e o que depende só do dono (secrets, limpeza de logs, configurações e a troca de visibilidade) ficou neste ticket.

## Checklist

Feito na sessão (no PR deste ticket):

- [x] Conta AWS e `emailDoDono` fora do `config/aws.json`; `infra/bin/app.ts` lê `AWS_CONTA` e `EMAIL_DO_DONO` do ambiente e falha com mensagem clara se faltar
- [x] `deploy.yml` lê os dois de `secrets` e confere se existem; `ci.yml` usa valores fictícios no synth
- [x] Número da conta, da conta de gerência e e-mails trocados por `<conta AWS>`, `<conta de gerência>` e `<e-mail do dono>` nos tickets, em `docs/aws/` e em `scripts/configurar-conta-aws.sh` (que agora exige `AWS_CONTA`)
- [x] `README.md` (seção Deploy) descreve os dois secrets
- [x] [ADR 0019](../../../docs/adr/0019-repositorio-publico-com-o-historico-mantido.md) registra a decisão e a exposição aceita no histórico

Do dono, nesta ordem:

- [ ] **Antes do merge do PR**: criar os secrets `AWS_CONTA` e `EMAIL_DO_DONO` em Settings → Secrets and variables → Actions. Sem eles o deploy da `main` falha logo no começo
- [ ] Rodar um scanner no histórico completo: `gitleaks detect --source . --log-opts="--all" --redact`; se achar credencial real, rotacioná-la antes de continuar
- [ ] **Apagar as execuções antigas do Actions** (os logs viram públicos e podem trazer a conta em texto): `gh run list --limit 1000 --json databaseId -q '.[].databaseId' | xargs -n1 gh run delete` (repetir até a lista esvaziar)
- [ ] Procurar a conta, a conta de gerência e os dois e-mails em issues, PRs e comentários já existentes e editar o que aparecer
- [ ] Settings → Actions → General: exigir aprovação para workflows de PR de fork e deixar o `GITHUB_TOKEN` só com leitura por padrão
- [ ] Settings → Code security: ligar secret scanning e push protection
- [ ] Conferir no console IAM que a trust policy da role `financial-app-deploy` continua restrita a este repositório
- [ ] Decidir se o repositório leva uma `LICENSE` (sem ela, todos os direitos ficam reservados)
- [ ] Settings → Emails do GitHub: ligar "Keep my email addresses private" para os commits futuros usarem o endereço `noreply` (o histórico antigo mantém o e-mail em 92 commits)
- [ ] Settings → General → Danger Zone → Change visibility → Public
- [ ] Depois: abrir um PR de teste e conferir em Billing que os minutos do Actions deixaram de contar, e que o deploy da `main` passa com os secrets
