# Itens do planejamento do mês

Type: task
Status: ready-for-agent
Blocked by: 40
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #103
Origem: [spec da v1](../spec.md), etapa 4; histórias de usuário 112, 117, 118, 119

## O que construir

O casal planeja o mês por item ("R$ 1.000 em alimentação") e vê o realizado, o previsto, o planejado e a porcentagem de cada um.

## Checklist

- [ ] Itens por mês, cada um de uma categoria (inclusive de transferência, para planejar o que guardar) e com um valor; edição só com internet
- [ ] Por item: realizado, previsto, planejado e %; "ainda dá para gastar" do item é planejado menos realizado e previsto, e o do mês é a soma do que falta em cada item, sem compensar item estourado
- [ ] Leitura do planejamento de um mês numa chamada só, já somada no servidor
- [ ] Testes de API com exemplos concretos
- [ ] Verificações do projeto rodando e PR aberto para `main`
- [ ] O "ainda dá para gastar" conta o previsto atrasado (data passada, sem confirmação; campo `atrasado` do ticket 43) até ele ser confirmado ou excluído (história 108): somar todo previsto do mês, não só o de data futura
