# Nomes nos avisos que ainda dizem "a outra pessoa"

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #162
Origem: [ticket 41](41-pessoa-autoria-e-parece-repetido.md): a tela de conflito e o aviso de exclusão da lista passaram a dizer o nome; sobraram dois textos que seguem genéricos

## O que construir

Trocar "a outra pessoa" pelo nome nos avisos que o ticket 41 não tocou, com `usePessoas().nomeDe` (`web/src/dados/index.ts`).

## Checklist

- [ ] `AvisoDaFila.tsx`: "N excluído pela outra pessoa" passa a dizer quem excluiu
- [ ] `ContasDaSemana.tsx`: "A outra pessoa excluiu este lançamento." passa a dizer o nome (o corpo do 410 traz `excluido_por`)
- [ ] Ajustar os testes de navegador que citam esses textos (`web/e2e/conflito.spec.ts`)
- [ ] Verificações do projeto rodando e PR aberto para `main`
