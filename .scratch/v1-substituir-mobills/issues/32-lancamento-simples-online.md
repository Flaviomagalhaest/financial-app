# Lançamento simples online

Type: task
Status: resolved
Blocked by: 30, 31
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #86
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 10-18 (versão simples)

## O que construir

Alguém do casal cria, edita e exclui um lançamento simples (conta, categoria, valor, data, descrição) e o vê numa lista. É a fatia mais fina de ponta a ponta: schema, API, tela e testes.

## Checklist

- [x] Tabela de lançamentos com identidade UUID gerada no aparelho, valor em centavos inteiros, tipo, situação, data, descrição e as colunas de autoria; categorias ligadas por tabela de associação ([ADR 0009](../../../docs/adr/0009-aurora-dsql-em-sao-paulo.md))
- [x] Contas e categorias mínimas (cadastro por script ou tela provisória) para o lançamento ter onde cair
- [x] Tela de lançamento com valor em destaque, teclado numérico próprio por centavos (`00` e apagar), alternância despesa/receita, conta, categorias e "Salvar" liberado só com valor e ao menos uma categoria
- [x] Editar e excluir pela lista; testes de API e de navegador cobrindo criar, editar e excluir
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- API em `backend/app/lancamentos.py`: `POST/GET /api/contas`, `POST/GET /api/categorias`, `POST/GET /api/lancamentos`, `PUT/DELETE /api/lancamentos/{id}`. Tabelas `contas`, `categorias`, `lancamentos` e `lancamento_categorias` (sem chave estrangeira, como manda o DSQL; a API confere as ligações). O `POST` repetido com o mesmo id devolve 200 sem duplicar; sem `situacao`, data futura nasce prevista (fuso de São Paulo).
- Cadastro de conta e categoria por tela provisória `#/cadastro` (trocada pela configuração no [ticket 74](74-cadastro-provisorio-de-contas-e-categorias.md)).
- As tabelas de exemplo do backup passaram a ter prefixo `exemplo_` para não colidir com as reais.
- Escolhas deixadas para os tickets seguintes: a exclusão apaga a linha de verdade, sem marca de exclusão, e a edição não leva versão; o [ticket 34](34-conflito-de-campos.md) precisa de ambos. A tela de edição busca a lista inteira para achar o lançamento; o [ticket 33](33-lancamento-sem-internet-fila-e-envio.md) a troca pela camada de dados do aparelho. Sem internet, salvar só mostra o aviso (ticket 33).
