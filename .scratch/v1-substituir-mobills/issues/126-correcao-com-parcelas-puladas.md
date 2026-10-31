# Correção do boleto com parcelas puladas e nada retroativo na correção

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `domain-modeling` para o `GLOSSARY.md`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #300
Origem: revisão (Spec) do [ticket 125](125-geracao-pula-o-passado.md): a regra "só de hoje em diante" ficou na geração, e a correção ainda tem dois furos

## O problema

1. **Data do boleto para frente perde as parcelas puladas.** Boleto de 10/08/2026 em 6 parcelas, lançado em 31/10: as parcelas 1 a 3 são puladas e `geradas` fica em 6. Uma correção (`PATCH /api/parcelamentos/{id}`) que muda a data para 10/12/2026 põe as três no futuro, mas `_correcoes` só olha as parcelas que existem e `_gerar_um_lote` começa em `geradas + 1`: elas nunca nascem, o total registrado fica menor e `parcelas_puladas` continua dizendo 3.
2. **Correção para o passado ainda é retroativa.** Mudar a data do boleto ou do parcelamento para trás move as parcelas existentes para o passado, e `alterar_parcelamento` chama `realizar_automaticos`, que realiza na hora as automáticas que passaram (`test_corrigir_a_data_para_o_passado_realiza_agora_a_parcela_automatica`). O `## Answer` do [ticket 87](87-recorrencia-com-inicio-no-passado.md) diz "Automática não lança realizadas retroativas". O mesmo vale para o reajuste da recorrência (`_reajustar_um_lote` em `backend/app/recorrencias.py`), que pode levar previstos para antes de hoje.

## Checklist

- [ ] Correção que leva parcela pulada para hoje ou depois a cria (sem reviver a parcela que o casal excluiu uma a uma); `parcelas_puladas` acompanha
- [ ] Correção que leva parcela para antes de hoje: decidir com teste (sai como pulada, ou fica prevista atrasada, sem realizar a automática) e registrar no `GLOSSARY.md` (**Correção do parcelamento**). Se a escolha não sair da regra do ticket 87, vira pergunta no [ticket 129](129-conferir-escolhas-do-125.md)
- [ ] Mesma conferência no reajuste "daqui para frente" da recorrência
- [ ] Testes de API em `backend/tests/test_parcelamentos.py` e `backend/tests/test_recorrencias.py`
