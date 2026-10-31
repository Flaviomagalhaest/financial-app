# Aviso de planejamento: sobras do ticket 109

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #249
Origem: [ticket 109](109-aviso-de-planejamento-casos-que-o-aparelho-nao-sabe.md): achados da revisão que ficaram fora dele

## Checklist

- [ ] **Teste do cartão arquivado**: compra não enviada num cartão arquivado conta pela fatura (hoje só há a leitura de `/api/cartoes?arquivados=true`, sem teste de navegador)
- [ ] **Teste do hook para o criar sem resposta**: só `semContarDeNovo` (puro) tem teste; falta cobrir `tentadoEm` gravado na fila e `contagensNoAparelho`
- [ ] **Recorrência enviada sem resposta** (`criar_recorrencia` com `talvezNoServidor`): conferir se tem a mesma contagem dupla
- [ ] **Tela de transferência**: o texto diz "Ainda dá para gastar" (usa `tipo="despesa"`), e `onEscolher` é vazio quando há duas categorias com item; decidir o texto e a escolha do item na transferência
- [ ] **ADR 0018**: uma linha dizendo que o aparelho lê também os cartões arquivados para achar a fatura
- [ ] Verificações do projeto rodando e PR aberto para `main`
