# Telas de tags e de manutenção de categorias e tags

Type: task
Status: open
Blocked by: 74
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #150
Origem: [ticket 40](40-categorias-e-tags.md) entregou só a API (`/api/tags`, `PATCH`, `/juntar` e `DELETE` de categorias e tags); a tela ficou de fora

## O que construir

Interface para o que a API do ticket 40 já faz: escolher e criar tags no próprio lançamento (hoje `TelaDeLancamento.tsx` só repassa as tags do lançamento existente) e as telas de configuração para renomear, arquivar, juntar e excluir categorias e tags, junto das telas do [ticket 74](74-cadastro-provisorio-de-contas-e-categorias.md). Só com internet.

## Checklist

- [ ] Campo de tags no lançamento, criando a tag nova ali mesmo
- [ ] Configuração de categorias: juntar e excluir (renomear e arquivar vêm do ticket 74)
- [ ] Configuração de tags: renomear, arquivar, juntar e excluir
- [ ] Decidir com o dono se despesa e receita precisam sempre ter uma categoria ativa (a API hoje deixa arquivar ou excluir a última)
- [ ] Testes de navegador
- [ ] Verificações do projeto rodando e PR aberto para `main`
