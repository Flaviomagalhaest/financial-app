# Pessoa, autoria e "Parece repetido"

Type: task
Status: ready-for-agent
Blocked by: 34
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #95
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 20, 61, 62

## O que construir

Cada lançamento diz de quem é (ou que é do casal), quem o criou e quem o alterou por último, e o app avisa quando o casal lançou a mesma coisa duas vezes.

## Checklist

- [ ] Campo pessoa (Flávio, esposa ou conjunto) no lançamento e no formulário
- [ ] Menu ⋯ > Informações com quem criou, quem alterou por último e quando (hora da ação no aparelho); origem "app" ou "importado do Mobills"
- [ ] "Parece repetido" quando chega lançamento da outra pessoa com mesmo valor, mesma conta ou cartão e data a até 1 dia, com "Manter os dois" ou "Excluir este"
- [ ] Testes de API e de navegador com dois contextos
- [ ] Verificações do projeto rodando e PR aberto para `main`
