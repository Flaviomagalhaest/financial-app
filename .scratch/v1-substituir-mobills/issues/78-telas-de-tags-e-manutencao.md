# Telas de tags e de manutenção de categorias e tags

Type: task
Status: open
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #150
Origem: [ticket 40](40-categorias-e-tags.md) entregou só a API (`/api/tags`, `PATCH`, `/juntar` e `DELETE` de categorias e tags); a tela ficou de fora

## O que construir

Interface para o que a API do ticket 40 já faz: escolher e criar tags no próprio lançamento (feito pelo [ticket 42](42-jornada-completa-do-lancamento-rapido.md), na folha de detalhes) e as telas de configuração para renomear, arquivar, juntar e excluir categorias e tags, na tela de contas e categorias que o [ticket 74](74-cadastro-provisorio-de-contas-e-categorias.md) entregou. Só com internet.

## Checklist

- [x] Campo de tags no lançamento, criando a tag nova ali mesmo (ticket 42)
- [x] Configuração de categorias: juntar e excluir (renomear e arquivar já existem, do ticket 74)
- [x] Configuração de tags: renomear, arquivar, juntar e excluir
- [x] Decidido com o dono: despesa e receita não precisam sempre ter uma categoria ativa; a API segue como está
- [x] Testes de navegador (`web/e2e/tags-e-manutencao.spec.ts`)
- [ ] Verificações do projeto rodando e PR aberto para `main`
