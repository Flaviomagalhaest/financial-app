# Recorrência com início no passado

Type: grilling
Status: ready-for-human
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

- [ ] O dono escolhe a regra e ela vai para `## Answer`
- [ ] Se a regra mudar: teste de API em `backend/tests/test_recorrencias.py` e ajuste em `_gerar_um_lote` ou na validação de `NovaRecorrencia` (`backend/app/recorrencias.py`)

## Notas

- Do [ticket 46](46-parcelamento-criar.md): a mesma pergunta vale para o parcelamento em boleto com a data no passado (pergunta 5 do [ticket 94](94-parcelamento-regras-provisorias.md)); decidir as duas juntas.
