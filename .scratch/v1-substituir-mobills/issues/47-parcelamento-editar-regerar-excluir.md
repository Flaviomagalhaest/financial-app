# Parcelamento: editar, regerar e excluir

Type: task
Status: ready-for-agent
Blocked by: 46
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #101
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 101, 102, 103, 104

## O que construir

O casal corrige um parcelamento errado sem refazer tudo.

## Checklist

- [ ] Editar descrição, tags ou pessoa vale para todas as parcelas, inclusive as realizadas
- [ ] Corrigir valor, número de parcelas ou data gera as parcelas de novo, com aviso quando uma realizada vai mudar; parcela editada à mão fica marcada e é preservada
- [ ] Excluir o parcelamento inteiro
- [ ] Testes de API
- [ ] Verificações do projeto rodando e PR aberto para `main`
