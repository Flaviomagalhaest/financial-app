---
status: accepted
---

# Previsto é uma situação do lançamento

Um compromisso futuro (a parcela que vem, o salário do mês que vem, o IPVA) é um lançamento com a situação **prevista**, que passa a **realizada** quando acontece. Não há uma entidade "compromisso" separada que gera um lançamento ao se realizar. Recorrência e parcelamento são regras que geram lançamentos: a compra parcelada não é um lançamento, só as parcelas são. Assim, editar, buscar, pôr tags, somar no planejamento e projetar o saldo funcionam igual para o que já aconteceu e para o que vai acontecer, e a compra parcelada nunca conta duas vezes.

## Considered Options

- **Compromisso separado do lançamento**: o futuro teria regras próprias, mas cada tela e cada soma teria de juntar duas listas, e a confirmação viraria a criação de um registro novo.
- **Compra parcelada como um lançamento só, com as parcelas como forma de exibir**: o valor inteiro cairia num mês e estouraria o planejamento dele.

## Consequences

- Só o realizado mexe no saldo da conta; o previsto entra na projeção e no "quanto ainda posso gastar".
- Recorrência sem fim gera previstos sem limite de tempo: o horizonte guardado ou calculado é decisão de implementação.
- Mudar uma recorrência nunca reescreve um realizado dela, e um previsto alterado à mão não é sobrescrito por uma mudança "daqui para frente". Já corrigir o valor, o número de parcelas ou a data de um parcelamento gera as parcelas de novo, inclusive as realizadas, com aviso.
