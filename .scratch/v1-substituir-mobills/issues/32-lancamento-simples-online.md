# Lançamento simples online

Type: task
Status: ready-for-agent
Blocked by: 30, 31
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #86
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 10-18 (versão simples)

## O que construir

Alguém do casal cria, edita e exclui um lançamento simples (conta, categoria, valor, data, descrição) e o vê numa lista. É a fatia mais fina de ponta a ponta: schema, API, tela e testes.

## Checklist

- [ ] Tabela de lançamentos com identidade UUID gerada no aparelho, valor em centavos inteiros, tipo, situação, data, descrição e as colunas de autoria; categorias ligadas por tabela de associação ([ADR 0009](../../../docs/adr/0009-aurora-dsql-em-sao-paulo.md))
- [ ] Contas e categorias mínimas (cadastro por script ou tela provisória) para o lançamento ter onde cair
- [ ] Tela de lançamento com valor em destaque, teclado numérico próprio por centavos (`00` e apagar), alternância despesa/receita, conta, categorias e "Salvar" liberado só com valor e ao menos uma categoria
- [ ] Editar e excluir pela lista; testes de API e de navegador cobrindo criar, editar e excluir
- [ ] Verificações do projeto rodando e PR aberto para `main`
