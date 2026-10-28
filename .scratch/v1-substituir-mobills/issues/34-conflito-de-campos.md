# Conflito de campos

Type: task
Status: ready-for-agent
Blocked by: 33
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #88
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 54, 55, 56, 57, 58, 59, 60

## O que construir

Quando os dois mexem no mesmo lançamento, mudanças em campos diferentes ficam as duas, e mudança no mesmo campo vira conflito decidido campo a campo ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)).

## Checklist

- [ ] Versão por campo no lançamento; o servidor aceita, mescla campos diferentes, aceita mudança idêntica, recusa como conflito (com campos divergentes, valor do outro lado, quem e quando, e se veio de uma regra) ou descarta por exclusão
- [ ] Marca "⚠ conflito", tela de decisão campo a campo ou descartar a minha mudança, e o aparelho mostra a versão do servidor enquanto o conflito espera
- [ ] Exclusão vence edição, com aviso e "Lançar de novo"; excluir algo que a outra pessoa mudou depois pergunta antes
- [ ] Testes de API para cada regra e testes de navegador com dois contextos fazendo o papel do casal
- [ ] Verificações do projeto rodando e PR aberto para `main`
- [ ] Trocar a exclusão física do ticket 32 por marca de exclusão (sem ela, "exclusão vence edição" não distingue excluído de inexistente) e dar versão ao `PUT /api/lancamentos/{id}`
- [ ] A confirmação com ajuste diferente sobre um previsto já confirmado devolve 409 "já confirmado com outros valores" (ticket 43), e o app só avisa e recarrega: levá-la para a tela de conflito, com os campos divergentes e quem confirmou
