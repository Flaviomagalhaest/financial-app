# Trocar o cadastro provisório de contas e categorias pelas telas de configuração

Type: task
Status: resolved
Blocked by: 32
Skills: `implement`, `tdd`; apoio: `artifact-design`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #140
Origem: [ticket 32](32-lancamento-simples-online.md): `#/cadastro` (`web/src/lancamentos/TelaDeCadastro.tsx`) é uma tela provisória que só cria conta e categoria; não edita, não arquiva, não reordena

## O que construir

Telas de configuração de categorias (e das contas, junto com o [ticket 36](36-contas-saldo-e-transferencia.md)) com criar, renomear e arquivar, no lugar da tela provisória. A tela some e o link "Contas e categorias" da Hoje aponta para a configuração.

## Checklist

- [x] Categorias: criar, renomear e arquivar (despesa, receita e transferência), só com internet
- [x] Remover `TelaDeCadastro` e a rota `#/cadastro`
- [x] Testes de API e de navegador
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- A tela é `#/configuracao` (`web/src/configuracao/TelaDeConfiguracao.tsx`). As contas continuam só com "criar" nela, para o app não ficar sem onde cadastrar conta; renomear e arquivar conta, junto com o saldo de abertura, é do [ticket 36](36-contas-saldo-e-transferencia.md).
- Categoria arquivada (`PATCH /api/categorias/{id}`, campo `arquivada`) sai das opções do lançamento novo, mas um lançamento que já a tinha a mantém ao ser editado. `GET /api/categorias` devolve todas, com `arquivada`.
- Sem teste unitário de `lerRota`: o web não tem runner de unidade, e a rota é coberta pelo teste de navegador.
