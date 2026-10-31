---
status: accepted
---

# O repositório fica público, com o histórico mantido

A cota de minutos do GitHub Actions no plano Free se esgotou e o CI/CD parou. Em repositório público os minutos dos runners hospedados padrão não são contados, então o dono decidiu tornar este repositório público. O número da conta AWS e o e-mail do dono saíram da árvore atual: a conta e o `emailDoDono` deixaram o `config/aws.json` e passaram a vir das variáveis `AWS_CONTA` e `EMAIL_DO_DONO` (secrets do repositório no deploy, variáveis de ambiente nos deploys à mão), e os tickets e documentos que os citavam passaram a dizer `<conta AWS>` e `<e-mail do dono>`. O histórico da `main` **não** foi reescrito: os commits antigos continuam trazendo esses valores.

## Considered Options

- **Pagar os minutos excedentes (limite de gasto no plano Free)**: mantém o repositório privado e o histórico fechado, mas passa a custar a cada deploy e a cada PR.
- **Rodar o CI num runner próprio (self-hosted)**: não gasta a cota hospedada, mas exige uma máquina ligada e a cobrança anunciada para runners próprios tem situação incerta.
- **Reescrever o histórico antes de publicar (`git filter-repo`)**: tiraria a conta e o e-mail dos commits antigos, mas quebra a regra de não reescrever a `main`, derruba os PRs e as branches em andamento e deixa os commits antigos em `refs/pull/*` até o suporte do GitHub limpar.
- **Publicar um repositório novo com um único commit**: não sobraria histórico a vazar, ao custo de perder o histórico e os PRs no repositório público.

## Consequences

- O número da conta AWS e dois e-mails do dono ficam visíveis para sempre no histórico público. Nenhum é credencial: o acesso à conta continua exigindo MFA e a role do deploy confia só neste repositório (OIDC). O dono aceitou essa exposição.
- O deploy exige os secrets `AWS_CONTA` e `EMAIL_DO_DONO`; sem eles o workflow falha logo no começo, dizendo qual falta. Como os logs do Actions de um repositório público são públicos, os secrets mascaram esses valores nos logs novos. Os logs de execuções anteriores precisam ser apagados antes da publicação.
- O `ci.yml` usa valores fictícios (`000000000000`, `ci@example.com`) no synth das pilhas, para rodar em PR de fork sem nenhum secret.
- Os workflows de deploy e de sincronização rodam só em `push`, então um fork não alcança a AWS nem o `PROJECT_TOKEN`. O `ci.yml` roda em PR de fork sem secrets; os workflows de fork de primeira contribuição devem exigir aprovação.
- Qualquer segredo que entrar no repositório daqui em diante vira público no push: a varredura de segredos e a proteção de push do GitHub ficam ligadas.
