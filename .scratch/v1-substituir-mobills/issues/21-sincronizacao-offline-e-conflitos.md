# Sincronização offline e conflitos

Type: grilling
Status: resolved
Blocked by: 08, 09, 12
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Issue: #62
Origem: fog "Sincronização offline e conflitos" do [mapa V1 que substitui o Mobills](../map.md), graduado agora que a plataforma ([ticket 08](08-plataforma-do-cliente.md)), o banco ([ticket 09](09-banco-de-dados-e-regiao.md)) e a arquitetura na AWS ([ticket 12](12-como-o-app-roda-na-aws.md)) estão decididos

## Question

Como um lançamento feito sem internet chega ao servidor, e o que acontece quando os dois editam o mesmo lançamento?

Cobrir: o que funciona sem internet (só criar lançamento ou também editar, confirmar previstos, apagar, mexer em regras e planejamento); o que o app guarda no aparelho para ler sem internet; quando e como a fila é enviada (no iPhone só com o app aberto); identidade do lançamento criado offline; o que o usuário vê enquanto algo não foi enviado; o que acontece quando os dois mexem no mesmo lançamento, e com apagar contra editar; geração de previstos por regra feita offline; como "quem criou e quem alterou por último" se registra.

## Checklist

- [x] Decisão registrada em `## Answer`
- [x] Vocabulário novo no `GLOSSARY.md` e ADR para o que for difícil de reverter

## Answer

Decidido com o dono em 2026-10-27. [ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md); os termos **não enviado** e **conflito** estão no [GLOSSARY.md](../../../GLOSSARY.md).

**O que funciona sem internet:** só lançamentos, um a um: criar (inclusive pelo favorito e pelo "repetir último"), editar, excluir e confirmar previsto. Planejamento, contas, cartões, categorias, tags, favoritos, configurações e mudanças "daqui para frente" de recorrência e parcelamento precisam de internet: o botão aparece desativado com "precisa de internet".

**Parcelado e recorrente sem internet:** entram na fila como um pedido só ("Geladeira em 10x, não enviado"), e o servidor gera as parcelas e os previstos ao receber. A regra de fatura e de geração fica só no servidor.

**O que o aparelho guarda:** o que é preciso para lançar (contas, cartões e faturas abertas, categorias, tags, favoritos, último lançamento, planejamento do mês com os totais) e a última resposta de cada tela já aberta, que mostra "atualizado às 14:32" sem internet. O aviso de planejamento soma o cache e a fila. Busca, histórico antigo e gráficos fora do cache precisam de internet: as somas ficam no servidor ([ADR 0009](../../../docs/adr/0009-aurora-dsql-em-sao-paulo.md)).

**Envio da fila:** sai assim que houver internet (no iPhone, ao abrir ou voltar para o app; no Android, também em segundo plano), com um botão "Enviar agora". Cada lançamento nasce com identidade gerada no aparelho, e reenviar nunca duplica. A fila sai em lote, na ordem em que as coisas foram feitas. Um lançamento recusado (o cartão foi arquivado enquanto isso, por exemplo) fica na fila marcado "não enviado: <motivo>", para corrigir ou descartar, e o resto segue.

**O que se vê enquanto não foi enviado:** o lançamento **não enviado** aparece nas listas com ⏳ e já conta no saldo e no aviso de planejamento do próprio aparelho; a tela Hoje mostra "3 lançamentos não enviados". O outro só o vê depois do envio. Algo não enviado há mais de 24 h deixa o aviso em destaque ("abra com internet para enviar"), e sair da conta com a fila cheia pede confirmação, porque apaga a fila.

**Os dois mexem no mesmo lançamento:** cada mudança leva a versão sobre a qual foi feita. Se o outro (ou uma regra) mudou depois os **mesmos campos**, o servidor recusa a mudança e ela vira um **conflito**. Campos diferentes entram sozinhos (ele troca o valor, ela põe a tag: ficam os dois), e mudança idêntica (os dois confirmaram o mesmo previsto com o mesmo valor) não é conflito. O dono escolheu decidir à mão, mesmo sendo raro.

- **Onde aparece:** no aparelho de quem fez a mudança, marcado "⚠ conflito", com "1 lançamento com conflito" na tela Hoje; o resto da fila segue. Quem fez a mudança decide numa tela só com os campos divergentes ("o seu: R$ 320" × "o da Fulana, às 14:32: R$ 230"), campo a campo, ou "Descartar a minha mudança". A outra pessoa não é avisada.
- **Enquanto espera:** o aparelho mostra a versão do servidor, com a marca "sua mudança espera decisão"; saldo e planejamento usam essa versão, e os dois aparelhos mostram o mesmo número.
- **Editar algo já excluído:** a exclusão vence; a edição é descartada com o aviso "Fulana excluiu este lançamento; sua alteração não foi salva" e o botão "Lançar de novo". Sem lixeira.
- **Excluir algo que o outro mudou depois:** é conflito ("Fulana alterou este lançamento depois de você. Excluir mesmo assim?"), com excluir ou manter.
- **Mudanças do próprio app** (recorrência alterada "daqui para frente", automático que vira realizado) contam como o outro lado, e a tela diz de onde veio ("a recorrência Luz, alterada pela Fulana"). Confirmar sem internet um previsto que sumiu porque a recorrência foi encerrada cai na regra da exclusão: aviso e "Lançar de novo".

**Lançamento repetido pelos dois:** quando chega um lançamento da outra pessoa com o mesmo valor, a mesma conta ou cartão e a data a até 1 dia de diferença, o app mostra "Parece repetido", com "Manter os dois" ou "Excluir este".

**Quem criou e quem alterou por último:** a pessoa vem do login (o servidor a tira do token) e a hora é a da ação no aparelho, não a do envio. Não aparece na lista nem no formulário: fica no menu ⋯ do lançamento > **Informações** ("Criado pelo Flávio em 12/03 14:32 · Alterado pela Fulana em 13/03 09:10"). Só a tela de conflito mostra quem e quando, porque precisa disso para decidir.

Fica para a spec: os números 24 h (aviso de não enviado) e 1 dia (parece repetido) são valores iniciais, a ajustar com o uso; e a primeira etapa da spec, que já testa o offline nos dois celulares ([ticket 08](08-plataforma-do-cliente.md)), passa a testar também o envio da fila e um conflito de verdade.
