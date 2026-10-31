# Itens do planejamento do mês pela tela

Type: task
Status: resolved
Blocked by: 54
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #207
Origem: [ticket 54](54-aba-mes.md) (revisão de spec: a história 112 da [spec](../spec.md), "quero criar o planejamento do mês com itens, cada um de uma categoria e com um valor", não tem tela; o 54 entregou só "Copiar do mês anterior", "Aplicar modelo padrão" e o modelo padrão)

## O que construir

Na seção "Itens do planejamento" da aba Mês (`web/src/mes/TelaDoMes.tsx`), o casal cria um item avulso (categoria e valor), muda o valor de um item e o exclui, sem passar pelo modelo padrão.

## Checklist

- [x] Criar item: `POST /api/planejamento/{mes}/itens` (id gerado no aparelho; reenviar devolve o gravado; 409 se a categoria já tem item no mês)
- [x] Mudar o valor: `PATCH /api/planejamento/itens/{id}`; excluir: `DELETE /api/planejamento/itens/{id}` (os lançamentos ficam, só deixam de contar no item)
- [x] Só com internet (ADR 0011), como copiar e aplicar; depois de cada mudança, buscar de novo a leitura do mês (`useMes(...).buscar`)
- [x] O valor em reais pode reusar `lerReais` de `web/src/mes/TelaDoModelo.tsx`, e a linha de categoria e valor, a do modelo padrão
- [x] Teste de navegador em `web/e2e/mes.spec.ts`
- [x] Verificações do projeto rodando e PR aberto para `main`
