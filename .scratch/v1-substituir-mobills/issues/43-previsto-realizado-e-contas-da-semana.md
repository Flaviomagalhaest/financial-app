# Previsto, realizado, confirmação e contas da semana

Type: task
Status: resolved
Blocked by: 32
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #97
Origem: [spec da v1](../spec.md), etapa 3; histórias de usuário 19, 105, 107, 108, 109, 110

## O que construir

Um compromisso futuro é um lançamento previsto que vira realizado ao ser confirmado ([ADR 0004](../../../docs/adr/0004-previsto-e-situacao-do-lancamento.md)); a tela inicial lembra o que confirmar.

## Checklist

- [x] Situação previsto/realizado: só o realizado mexe no saldo; confirmar ajusta valor, data ou conta, inclusive sem internet (entra na fila). Sem internet: [ticket 33](33-lancamento-sem-internet-fila-e-envio.md)
- [x] Previsto com data passada sem confirmação fica atrasado e continua contando na projeção e no "ainda dá para gastar". A soma é dos tickets [49](49-itens-do-planejamento.md) e [58](58-aba-futuro-e-projecao-de-saldo.md)
- [x] "N contas da semana para confirmar" na Hoje, com atrasados e previstos dos próximos 7 dias, em ordem de data, com "Confirmar" em um toque ou "Ajustar"
- [x] Testes de API e de navegador
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- API em `backend/app/lancamentos.py`: cada `Lancamento` traz `atrasado` (previsto com data antes de `hoje()`, o dia de São Paulo). `POST /api/lancamentos/{id}/confirmar` vira o previsto em realizado, com `valor_centavos`, `data` e `conta_id` opcionais. A conta passa por `conferir_conta`, então a confirmação não leva o previsto para uma conta arquivada. Confirmar de novo sem ajuste diferente (a fila reenviou, a outra pessoa confirmou em um toque) devolve o gravado com 200; com ajuste diferente dá 409, para não perder a mudança em silêncio (ADR 0011). A tela de conflito fica no [ticket 34](34-conflito-de-campos.md).
- `GET /api/contas-da-semana` é a leitura do bloco: previstos com data até hoje + `contasDaSemanaDias` (`config/valores-iniciais.json`), do mais antigo ao mais novo, com os atrasados primeiro. O saldo só dos realizados veio do [ticket 36](36-contas-saldo-e-transferencia.md). Os testes de API cobrem que o previsto não mexe no saldo e que a confirmação o traz para dentro.
- No app, o bloco `ContasDaSemana` fica na aba Hoje, com "Confirmar" em um toque e "Ajustar" (teclado por centavos, data e conta). A tela de lançamento troca a situação à mão em Detalhes (história 19), e o Histórico mostra "previsto, atrasado". O `hoje()` do app (`web/src/lancamentos/datas.ts`) passou a ser o dia de São Paulo, igual ao da API.
- Pendências gravadas: a confirmação sem internet vai para o [ticket 33](33-lancamento-sem-internet-fila-e-envio.md) e o conflito da confirmação para o [34](34-conflito-de-campos.md). O automático fica fora das contas da semana nos [44](44-recorrencia-criar.md) e [46](46-parcelamento-criar.md). O atrasado conta no "ainda dá para gastar" ([49](49-itens-do-planejamento.md)) e na projeção ([58](58-aba-futuro-e-projecao-de-saldo.md)), e o bloco entra na leitura única da Hoje no [53](53-aba-hoje.md). A data da confirmação de um previsto futuro é decisão do dono no [79](79-data-da-confirmacao-de-um-previsto-futuro.md), e a transferência prevista atrasada e a confirmação dela ficam no [80](80-transferencia-prevista-atrasada-e-confirmacao.md).
