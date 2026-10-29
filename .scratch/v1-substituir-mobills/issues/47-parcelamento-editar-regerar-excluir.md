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

## Notas

- Do [ticket 46](46-parcelamento-criar.md): as parcelas de um parcelamento são os lançamentos com o `parcelamento_id` dele; o id de cada uma é `uuid5(parcelamento, número)` e `parcelamentos.geradas` diz até que parcela já gerou. Ainda não há marca de alterado à mão no lançamento (a mesma falta do [45](45-recorrencia-mudar.md)). `PATCH` numa parcela do cartão já mantém a distância de n - 1 faturas (`faturas.mes_da_parcela`). A tabela `parcelamentos` não tem marca de exclusão. A regeração precisa recalcular a fatura das parcelas com a data nova e, na parcela automática, o `realiza_em`.
