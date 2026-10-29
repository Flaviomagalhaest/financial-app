# Conflito de campos

Type: task
Status: resolved
Blocked by: 33
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #88
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 54, 55, 56, 57, 58, 59, 60

## O que construir

Quando os dois mexem no mesmo lançamento, mudanças em campos diferentes ficam as duas, e mudança no mesmo campo vira conflito decidido campo a campo ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)).

## Checklist

- [x] Versão por campo no lançamento; o servidor aceita, mescla campos diferentes, aceita mudança idêntica, recusa como conflito (com campos divergentes, valor do outro lado, quem e quando, e se veio de uma regra) ou descarta por exclusão
- [x] Marca "⚠ conflito", tela de decisão campo a campo ou descartar a minha mudança, e o aparelho mostra a versão do servidor enquanto o conflito espera
- [x] Exclusão vence edição, com aviso e "Lançar de novo"; excluir algo que a outra pessoa mudou depois pergunta antes
- [x] Testes de API para cada regra e testes de navegador com dois contextos fazendo o papel do casal
- [x] Verificações do projeto rodando e PR aberto para `main`
- [x] Trocar a exclusão física do ticket 32 por marca de exclusão (sem ela, "exclusão vence edição" não distingue excluído de inexistente) e dar versão ao `PUT /api/lancamentos/{id}`
- [x] A confirmação com ajuste diferente sobre um previsto já confirmado devolve 409 "já confirmado com outros valores" (ticket 43), e o app só avisa e recarrega: levá-la para a tela de conflito, com os campos divergentes e quem confirmou

## Notas da implementação

- **Servidor** (`backend/app/lancamentos.py`): o lançamento traz `versao`, que sobe a cada mudança aceita (antigo, sem versão, conta como 1). A tabela `lancamento_campos` guarda por campo a versão, quem, quando e a `origem` da regra (vazia até os tickets 44 e 45; `_registrar_mudancas(..., origem=)` já a recebe). A gravação só passa se a versão ainda for a lida; senão a transação recomeça (`em_transacao`), o que vale também no Postgres local.
- **Edição**: virou `PATCH /api/lancamentos/{id}` com só os campos mudados e a `versao` sobre a qual a mudança foi feita, no lugar do `PUT` de corpo inteiro: com o corpo inteiro, o servidor não distingue o campo que a pessoa mudou do que ela só repetiu, e a mescla de campos diferentes não funciona. Campo que o outro lado mudou depois da versão para outro valor recusa a mudança inteira com 409 (`Conflito`: o lançamento do servidor e os campos, com quem, quando, `por_voce` e `origem`); mudança igual à gravada passa. Só mudar a data refaz a situação pela data se ninguém mudou a situação depois, para não desfazer a confirmação do outro.
- **Exclusão**: marca `excluido_em` e `excluido_por` e tira as ligações com categorias e tags; todas as leituras e o saldo ignoram o marcado. Editar, confirmar ou reenviar o criar de algo excluído dá 410 (`Exclusao`); no lote, `descartada` com a `exclusao`. `DELETE ?versao=N` dá 409 se o outro lado mudou depois; sem `versao`, exclui de qualquer jeito.
- **Confirmação**: aceita `versao` e só os ajustes que a pessoa fez; ajuste num campo que o outro lado mudou depois é 409, e o já confirmado com outros valores também, com quem confirmou como o outro lado dos campos. O `ContasDaSemana` manda só o que mudou e leva o 409 para a tela de conflito, guardando a confirmação na fila como edição já em conflito (`guardarConflito`).
- **Lote**: `editar` é `{id, alteracao}` e `excluir` leva `versao`. Uma PWA antiga, ainda não atualizada, que mande o formato velho recebe recusa ("o servidor não aceitou este lançamento"), e a mudança fica no aparelho para corrigir depois que o app atualiza: não se perde. O app ainda não está em uso antes da virada (ticket 69), então não há compatibilidade com o formato antigo.
- **Aparelho** (`web/src/dados/fila.ts`): o item guarda a versão do servidor que a tela mostrava (`base`) e sobe só o que mudou desde ela; item sem base, de uma versão anterior do app, sobe tudo sobre a versão 0. O que muda enquanto o lote sobe passa a valer sobre a versão aceita. Conflito e exclusão que venceu ficam no item e não sobem até a pessoa decidir; enquanto isso a lista guardada tem a versão do servidor.
- **Telas**: o Histórico marca "⚠ conflito: sua mudança espera decisão" com "Decidir", e o aviso de exclusão com "Lançar de novo" (cria outro lançamento, com outra identidade) e "Dispensar". `#/conflito/<id>` mostra cada campo em conflito com "O seu: …" e "O da outra pessoa, às 14:32: …" para escolher, ou "Descartar a minha mudança"; numa exclusão, "Excluir mesmo assim" ou "Manter o lançamento". A Hoje mostra "1 lançamento com conflito: decida no Histórico.". Os nomes ficam "a outra pessoa" até o ticket 41.
- **Combinação inválida na decisão** (o outro trocou o tipo e eu fiquei com a minha categoria do tipo antigo): o servidor recusa com o motivo ("categoria de despesa num lançamento de receita"), e o lançamento fica "não enviado: <motivo>" para corrigir.
- **Backup**: formato 7, com conversor da 6 (lançamentos sem versão e sem marca; `lancamento_campos` vazia).
- **Reserva**: commitada na própria branch de trabalho, como no ticket 33.
- **Pendências**: linhas novas nos tickets [35](35-teste-nos-dois-celulares.md) (conferir no DSQL o conflito e o `ON CONFLICT DO UPDATE` de `lancamento_campos`), [41](41-pessoa-autoria-e-parece-repetido.md) (nomes e hora da ação no aparelho na tela de conflito), [45](45-recorrencia-mudar.md) (gravar a `origem`), [77](77-ligar-o-csv-de-planilha-ao-esquema-real.md) (o marcado como excluído fica fora da planilha) e [83](83-confirmar-previsto-sem-internet-pela-fila.md) (a confirmação pela fila com `versao` e só os ajustes).
