# Trocar o cadastro provisório de contas e categorias pelas telas de configuração

Type: task
Status: open
Blocked by: 32
Skills: `implement`, `tdd`; apoio: `artifact-design`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #140
Origem: [ticket 32](32-lancamento-simples-online.md): `#/cadastro` (`web/src/lancamentos/TelaDeCadastro.tsx`) é uma tela provisória que só cria conta e categoria; não edita, não arquiva, não reordena

## O que construir

Telas de configuração de categorias (e das contas, junto com o [ticket 36](36-contas-saldo-e-transferencia.md)) com criar, renomear e arquivar, no lugar da tela provisória. A tela some e o link "Contas e categorias" da Hoje aponta para a configuração.

## Checklist

- [ ] Contas: criar, renomear, informar o saldo de abertura e arquivar, com a API que o [ticket 36](36-contas-saldo-e-transferencia.md) entregou (`PUT /api/contas/{id}`)
- [ ] Categorias: criar, renomear e arquivar (despesa, receita e transferência), só com internet
- [ ] Remover `TelaDeCadastro` e a rota `#/cadastro`
- [ ] Testes de API e de navegador
- [ ] Verificações do projeto rodando e PR aberto para `main`
