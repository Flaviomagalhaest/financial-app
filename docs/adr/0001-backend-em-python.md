---
status: accepted
---

# Backend em Python, com o app em outra linguagem

O backend do app é escrito em Python, embora o app da web e do celular não seja em Python. TypeScript nas duas pontas daria uma linguagem só e tipos compartilhados, mas o dono quer o backend em Python para abrir caminho a cálculos de ciência de dados sobre o histórico financeiro, se a plataforma evoluir.

## Consequences

- O app e a API não compartilham tipos: o contrato entre eles precisa ser explícito e verificável, e é decidido no ticket [Como o app roda na AWS](../../.scratch/v1-substituir-mobills/issues/12-como-o-app-roda-na-aws.md).
