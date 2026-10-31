# Recorrência com início no passado

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se a regra mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #168
Origem: [ticket 44](44-recorrencia-criar.md) (revisão: a spec não diz o que acontece com as ocorrências antes de hoje)

## A pergunta

`POST /api/recorrencias` gera todas as ocorrências desde o `inicio`. Com o início no passado:

- a de valor estimado (o salário, a luz) gera um previsto **atrasado** por ocorrência que já passou, e todos aparecem nas contas da semana;
- a automática (o Spotify) gera as que passaram já **realizadas**, mexendo no saldo.

Quem cadastra hoje o salário que caiu no dia 5 com início em 05/10 ganha o de outubro atrasado para confirmar; quem cadastra com início em 2019 ganha dezenas. E o salário lançado hoje como recorrente nasce previsto (pede confirmação), não realizado como um lançamento de hoje.

## Opções

- **Deixar como está**: o início é a primeira ocorrência, passada ou não; quem não quer o passado põe o início na próxima.
- **Gerar só a partir de hoje**: as ocorrências antes de hoje não viram lançamento.
- **Recusar início antes de hoje** (422), salvo a de hoje.
- Em qualquer uma: a ocorrência de **hoje** nasce realizada quando vem do novo lançamento (o casal está registrando o que aconteceu)?

## Checklist

- [x] O dono escolhe a regra e ela vai para `## Answer`
- [x] Se a regra mudar: o ajuste vai para o [ticket 125](125-geracao-pula-o-passado.md): teste de API em `backend/tests/test_recorrencias.py` e ajuste em `_gerar_um_lote` ou na validação de `NovaRecorrencia` (`backend/app/recorrencias.py`)

## Answer

Decidido pelo dono (grilling), junto com a pergunta 5 do [ticket 99](99-parcelamento-regras-provisorias.md):

- **Gerar só a partir de hoje**: ocorrência anterior a hoje não vira lançamento (nem atrasada, nem realizada). O calendário segue contado desde o `inicio`.
- **A ocorrência de hoje** vinda do novo lançamento nasce **realizada**, tanto a de valor estimado quanto a automática.
- **`vezes` conta as ocorrências puladas**: o fim da regra não muda por causa do passado.
- **Regra inteira no passado** (`ate` ou o fim por `vezes` antes de hoje): 422 "a recorrência termina antes de hoje".
- **Automática** não lança realizadas retroativas: o saldo não muda por data passada.
- **Boleto parcelado com data no passado**: mesma regra; as parcelas puladas contam na numeração (comprando "3/10" hoje, a 1ª lançada é a 4/10), o total informado fica e a resposta avisa quantas foram puladas. O cartão segue o ticket 99.

Implementação: [ticket 125](125-geracao-pula-o-passado.md).

## Notas

- Do [ticket 46](46-parcelamento-criar.md): a mesma pergunta vale para o parcelamento em boleto com a data no passado (pergunta 5 do [ticket 99](99-parcelamento-regras-provisorias.md)); decidir as duas juntas.
