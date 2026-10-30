# Aba Futuro e projeção de saldo

Type: task
Status: resolved
Blocked by: 48, 51
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #112
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 135, 136

## O que construir

O casal sabe se vai fechar no azul nos próximos meses.

## Checklist

- [x] Projeção com o realizado no passado e duas linhas adiante (só previstos, e descontando o que falta do planejamento), mais tabela dos próximos meses
- [x] A fatura é descontada no mês dela
- [x] Testes de API com exemplos concretos
- [x] Verificações do projeto rodando e PR aberto para `main`
- [x] A linha "só previstos" conta também o previsto atrasado (data passada, sem confirmação; campo `atrasado` do ticket 43) até ele ser confirmado ou excluído (história 108), e não só os de data futura

## Notas

- API em `backend/app/projecao.py`: `GET /api/futuro` é a leitura única da aba (o app a guarda para mostrar sem internet). Traz o `saldo_hoje_centavos` (a soma das contas, arquivadas inclusive), o `passado` (o saldo no fim de cada um dos 12 meses anteriores, só com os realizados) e os `proximos_meses` (12, a partir do mês atual), cada um com `previstos_centavos` (receitas menos despesas previstas nas contas), `faturas_centavos` (o que falta pagar das faturas do mês), `planejamento_centavos` (o que falta dos itens de despesa), `so_previstos_centavos` e `com_planejamento_centavos` (o saldo no fim do mês em cada linha).
- A fatura sai no mês dela (ADR 0003, história 136): o `a_pagar` de cada fatura menos o saldo anterior que ela recebeu (que já contou na fatura de onde veio). O que falta das faturas de meses que passaram sai no mês atual. As compras e parcelas previstas no cartão entram pela fatura, não pelos previstos. O pagamento de fatura previsto não conta.
- O previsto atrasado das contas conta no mês atual até ser confirmado ou excluído (história 108); no cartão, ele já está na fatura.
- No passado, cada conta entra na soma a partir da sua data de abertura (ADR 0007); antes da primeira abertura, o mês fica sem ponto.
- Funções públicas novas: `lancamentos.contas_com_saldo` e `VALOR_NA_CONTA`, `cartoes.titulares`, `planejamento.ler` (era `_ler`) e `planejamento.a_lancar_nas_despesas`.
- App: aba Futuro em `web/src/futuro/` (gráfico em SVG com o realizado e as duas linhas tracejadas, leitura do mês embaixo do gráfico, tabela dos próximos meses) e `useFuturo` na camada de dados. Cores das séries em `--serie-1` e `--serie-2` no `estilo.css`, conferidas para daltonismo nos dois temas.
- Pendências: as regras que o 58 decidiu sozinho (item de transferência e de receita fora da linha com planejamento, ajuste de fatura, mês sem planejamento, passado por abertura, pagamento previsto, 12 meses) são decisão do dono no [ticket 106](106-projecao-de-saldo-regras-provisorias.md). A fatura importada do Mobills precisa sair paga para não entrar na projeção do mês atual: nota no [ticket 68](68-importador-do-mobills-parcelamentos-pendentes-e-ajustes.md). A falha intermitente de `cartoes.spec.ts`, que também acontece na `main`, foi para o [ticket 90](90-teste-do-recusado-intermitente.md).
