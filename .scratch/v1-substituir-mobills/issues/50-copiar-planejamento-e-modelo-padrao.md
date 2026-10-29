# Copiar planejamento e modelo padrão

Type: task
Status: resolved
Blocked by: 49
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #104
Origem: [spec da v1](../spec.md), etapa 4; histórias de usuário 113

## O que construir

O casal monta o mês copiando o anterior ou um modelo padrão em vez de começar do zero.

## Checklist

- [x] Copiar o planejamento do mês anterior para um mês vazio
- [x] Modelo padrão (conjunto de itens com valor) editável nas configurações e aplicável a um mês
- [x] Testes de API
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas da implementação

- Cópia: `POST /api/planejamento/{mes}/copiar` com `{"de": "YYYY-MM"}`; o destino precisa estar vazio (409) e a origem ter item (422).
- Modelo padrão: tabela `modelo_do_planejamento` (migration 0022, uma linha por categoria), `GET`/`PUT /api/planejamento/modelo` (o PUT troca o conjunto inteiro) e `POST /api/planejamento/{mes}/aplicar-modelo` (mês vazio). Juntar categorias soma o item do modelo e excluir categoria com item no modelo é recusado.
- Backup na versão 10, com conversor da 9 (modelo vazio).
- Só a API; a tela de configurações e o botão de copiar/aplicar ficam para a interface do planejamento.
