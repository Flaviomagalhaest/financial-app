---
status: accepted
---

# A mudança da recorrência vai pela fila, e a regra sem versão recusa o campo que mudou depois

Mudar uma recorrência "daqui para frente", encerrá-la e excluí-la passam a valer sem internet: cada uma entra na fila do aparelho como um pedido só (`alterar_recorrencia` e `excluir_recorrencia` em `POST /api/lancamentos/lote`) e o servidor reajusta ou tira os previstos ao receber, como já faz com a recorrência e o parcelamento novos. Isso abre uma exceção na [ADR 0011](0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md), que deixava toda mudança de regra só com internet. Quem decidiu foi o dono, no ticket 96: a conta que muda de valor ou a assinatura cancelada aparecem na hora de pagar, muitas vezes sem rede.

O aparelho não repete a regra: enquanto a mudança não sobe, ele mostra a regra com a mudança por cima e esconde só os previstos que o fim ou a exclusão vão tirar; o valor novo dos previstos chega na leitura seguinte ao envio. Mudar só um mês e pular um mês já eram mudanças de um lançamento e seguem como antes.

A regra não tem versão. Em vez de criar uma, o pedido da fila leva em `antes` o que a tela mostrava nos campos que ele muda. Se a outra pessoa (ou outro aparelho) mudou depois um desses campos para outro valor, o servidor recusa a mudança com o motivo ("a regra mudou depois (valor): confira e mude de novo"), e ela fica no aparelho até ser descartada. Campos diferentes se mesclam, e a mudança igual à que já chegou passa, o que torna o reenvio inofensivo. Nada se perde em silêncio, como o dono pediu na ADR 0011, sem uma segunda tela de conflito.

## Considered Options

- **Só com internet, como o parcelamento**: o mais simples e fiel à ADR 0011, e foi o caminho da correção do parcelamento (ticket 98). O dono preferiu a fila para a recorrência.
- **O último a chegar fica com a regra**: era o comportamento do `PATCH`. Com a fila, a mudança feita dias antes sem internet sobrescreveria em silêncio o reajuste que a outra pessoa fez depois.
- **Versão na regra e conflito campo a campo, como no lançamento**: pediria versão por campo na recorrência e uma tela de conflito própria, para um caso raro. A recusa com o motivo deixa a pessoa refazer a mudança vendo a regra nova.
- **Repetir a regra no aparelho para mostrar os previstos reajustados**: o que a ADR 0011 queria evitar. Esconder os previstos que saem é uma comparação de data e número, não a regra.

## Consequences

- A ação `alterar_recorrencia` refaz até o horizonte os previstos em transações próprias, como a geração: o app soma esses previstos aos das outras regras do lote e respeita o mesmo teto do parcelamento (`maximoDeParcelas`) para o lote caber no tempo da Lambda.
- O `PATCH /api/recorrencias/{id}` continua sem `antes`, com o último a chegar ficando com a regra; o app não o usa mais.
- A edição de um previsto sem internet que colide com a mudança da regra segue virando conflito "O da regra <origem>" (ADR 0011).
- A recorrência criada no aparelho que talvez já tenha subido se exclui pela fila em vez de se descartar, e a descartada no meio do envio é excluída logo depois que ele volta aceito.
