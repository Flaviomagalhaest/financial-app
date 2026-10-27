# Login no app

Type: task
Status: ready-for-agent
Blocked by: 28
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #84
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 4, 5, 6, 7, 8, 9

## O que construir

Cada um do casal entra com e-mail e senha num formulário dentro do app e fica logado por anos; a API aceita só quem tem JWT válido.

## Checklist

- [ ] Formulário no app com SRP e cliente público do Cognito, isolado num módulo de login que é o único a conhecer o Cognito
- [ ] Refresh token de 10 anos no IndexedDB (nunca em cookie) e token de acesso de 15 minutos; sem internet e com o acesso vencido o app segue usável
- [ ] A API depende só de um JWT padrão (emissor e audiência em configuração) e tira a pessoa do token; testes com dois usuários por JWT de teste
- [ ] Só os dois usuários existem, sem cadastro público; o dono consegue desconectar todas as sessões de um celular perdido
- [ ] Sair da conta com itens não enviados pede confirmação (o aviso só ganha efeito quando a fila existir, [ticket 33](33-lancamento-sem-internet-fila-e-envio.md))
- [ ] Verificações do projeto rodando e PR aberto para `main`
