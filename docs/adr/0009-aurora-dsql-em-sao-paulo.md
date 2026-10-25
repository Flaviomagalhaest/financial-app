---
status: accepted
---

# Aurora DSQL em São Paulo, com o app inteiro numa região

Os dados do app ficam no Aurora DSQL, em sa-east-1 (São Paulo), e todo o resto do app (API, backup, hospedagem, login) fica na mesma região. O DSQL é a única opção com SQL para as somas por mês, categoria e tag sobre anos de histórico e com custo perto de zero (franquia de 100 mil DPU e 1 GB por mês; sem ela, centavos). São Paulo custa centavos a mais que a Virgínia no DSQL e dá latência de 10 a 30 ms em vez de cerca de 125 ms. Começar em us-east-2, onde a SCP da organização liberava, e migrar depois obrigaria a refazer o pool de usuários, buckets e segredos, então a SCP foi alterada para liberar sa-east-1.

## Considered Options

- **DynamoDB**: centavos e PITR de 35 dias, mas não soma nem agrupa: cada dashboard leria todos os itens do período ou o app manteria agregados a cada escrita. A franquia é dividida com outro projeto da organização.
- **Aurora Serverless v2 com pausa**: Postgres completo com PITR, mas de US$ 3 a 7 por mês e 15 s ou mais para voltar da pausa.
- **us-east-2 agora e São Paulo depois**: era a única região de trabalho liberada pela SCP e tem os mesmos créditos, mas a migração custa o trabalho que se quer evitar.

## Consequences

- O schema fica no subconjunto do DSQL: sem triggers nem PL/pgSQL, até 3.000 linhas e 10 MiB por transação (a importação do Mobills grava em lotes), concorrência otimista com nova tentativa no erro de serialização e autenticação só por IAM. Sair do DSQL para um Postgres completo é fácil; o inverso não.
- Região e endpoint ficam só em configuração e as migrations são versionadas no repositório.
- Sem PITR: o backup é a exportação completa diária do próprio app num bucket S3 com versões, 90 dias e Object Lock, na mesma conta. A perda máxima é de 1 dia, e perder a conta leva o backup junto; a cópia fora da AWS fica para depois da v1.
- O histórico mora numa tabela só, sem agregados nem partições, com o mês em que cada lançamento conta gravado nele. Agregado mensal só entra se um dashboard passar de 1 s no servidor.
- A SCP da raiz da organização passou a liberar sa-east-1 para todas as contas. Se ela for reaplicada sem São Paulo, o app para de funcionar.
- A escolha do DSQL é revista se a primeira conexão depois do cluster parado passar de 5 s.
