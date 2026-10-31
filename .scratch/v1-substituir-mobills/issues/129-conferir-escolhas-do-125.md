# Conferir as escolhas do ticket 125 sem decisão do dono

Type: grilling
Status: ready-for-human
Blocked by: —
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se a regra mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #303
Origem: [ticket 125](125-geracao-pula-o-passado.md) (revisão: o ticket 87 não decidiu estes pontos, e o 125 os fixou)

## As perguntas

1. **Boleto inteiro no passado é recusado** (422 "o parcelamento termina antes de hoje"), por analogia com a recorrência. Alternativa: aceitar e gravar o parcelamento sem parcelas, só como registro.
2. **A de hoje nasce realizada em toda recorrência nova**, também na de valor fixo que não é automática. O `## Answer` do 87 cita "a de valor estimado quanto a automática". Alternativa: a fixa não automática nasce prevista.
3. **A de hoje só nasce realizada na criação.** Gerada depois (pela tarefa diária ou por uma mudança da regra), a estimada de hoje nasce prevista e pede confirmação.
4. **"Pulada" tem dois sentidos**: o mês que o casal pulou (excluído) e a parcela que não nasceu por estar no passado (`parcelas_puladas`). Trocar a palavra do segundo (por exemplo "anteriores")?
5. **Precisa de ADR?** "A geração só lança de hoje em diante" mexe no previsto e no realizado da ADR 0004; hoje o registro é o ticket 87 e o glossário.

## Checklist

- [ ] O dono responde cada pergunta e a resposta vai para `## Answer`
- [ ] Se uma regra mudar: teste de API e ajuste em `backend/app/recorrencias.py` ou `backend/app/parcelamentos.py`, e o verbete no `GLOSSARY.md`
