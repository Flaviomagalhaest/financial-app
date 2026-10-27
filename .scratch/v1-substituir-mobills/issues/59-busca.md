# Busca

Type: task
Status: ready-for-agent
Blocked by: 54, 55
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #113
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 137, 138, 139, 140, 141, 142, 143, 144, 145

## O que construir

O casal acha qualquer lançamento desde 2019 pela lupa, de qualquer aba ([ADR 0013](../../../docs/adr/0013-busca-por-data-da-compra-e-fatura-a-parte.md), [ticket 24](24-busca-e-filtros-salvos.md)).

## Checklist

- [ ] Texto livre e filtros combinados; período pela data da compra e filtro Fatura à parte; linha fixa explicando a diferença para a aba Mês
- [ ] Compra parcelada numa linha que abre as parcelas (cada parcela uma linha com o filtro Fatura); totais no topo com previstos à parte e transferências fora; ordenação e paginação sem teto
- [ ] Atalhos "ver os lançamentos" do Mês e dos Cartões abrem a busca filtrada
- [ ] Sem internet, resultado parcial do que o aparelho guarda, com aviso
- [ ] Testes de API e de navegador
- [ ] Verificações do projeto rodando e PR aberto para `main`
