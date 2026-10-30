# Importador do Mobills: parcelamentos, pendentes e ajustes

Type: task
Status: resolved
Blocked by: 67, 47, 39
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #122
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 171, 172, 173, 174

## O que construir

O histórico importado já traz o futuro e as faturas certos, e o importador gera um backup válido que a restauração grava ([ADR 0008](../../../docs/adr/0008-ajuste-de-fatura-fica-na-fatura.md), [ADR 0012](../../../docs/adr/0012-exportacao-unica-zip-de-csvs-e-restauracao-so-em-banco-vazio.md)).

## Checklist

- [x] Parcelas reagrupadas em parcelamentos, com as parcelas futuras que faltam geradas como previstas
- [x] Pendentes que não são parcela: previstos avulsos se de meses seguintes ao export, descartados se do mês do export ou anteriores
- [x] `Reajuste de fatura` vira ajuste de fatura; faturas importadas nascem com o mês da fatura do rótulo, fechadas e pagas, sem datas nem pagamento de fatura
- [x] Saída é um backup válido; teste de que ele restaura num banco vazio
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

- **Backup**: `uv run python -m app.mobills <geral> <faturas> <planilha.xlsx> --backup <backup.zip>` grava o zip só quando não há impedimento (sai com 2 e não grava enquanto houver). `app/mobills/backup.py` monta o zip da versão atual do formato sem banco, pelo esquema de `backend/app/esquemas_do_formato.json` (saiu de `tests/` para o importador ler) e pelo mesmo `montar_backup` do gerador. O teste restaura o zip num banco vazio e exige o mesmo zip de volta no `gerar_backup`; o `app.restauracao` mostra "exportado de novo: mesmo zip". Uma coluna nova obrigatória faz esse teste falhar até o importador dar o valor dela.
- **O que entra**: conta e cartões do cadastro (os arquivados com `arquivado_em`), categorias e tags pelo nome, tudo com `fonte = 'mobills'` e `criado_por = 'mobills'` (um só, para o "Parece repetido" não comparar o histórico com ele mesmo), a pessoa do de-para conferida contra `PESSOAS` (impedimento se não for do casal) e ids `uuid5` vindos do conteúdo e da ordem: os mesmos exports dão o mesmo zip.
- **Parcelas**: a sequência que chega ao último mês do geral sem a última parcela ganha as que faltam como previstas, com o valor da última que veio. No cartão, com a data da compra e uma fatura depois da outra; no boleto, um mês depois da 1ª, que é recuada quando veio antes do histórico. No backup, cada parcela tem o id `uuid5(parcelamento, número)`, `geradas` = `parcelas`, o do cartão é automático e o do boleto não. As de antes do histórico não entram, mas contam no `valor_total_centavos` com o valor da primeira que veio. A sequência quebrada, a receita parcelada e o `(1/1)` entram avulsos, sem parcelamento e sem gerar nada: os pedaços de uma sequência quebrada seriam dois parcelamentos da mesma compra.
- **Pendentes avulsos** (termo novo no glossário): o mês do export é o último mês com lançamento pago no geral, o mesmo em que a Conferência termina. O pendente que não é parcela e não casou com fatura, desse mês ou de antes, é descartado e aparece no "Por quê" da Conferência; o de depois entra previsto. O que casou com uma linha de fatura fica, porque a fatura prova a compra.
- **Ajustes e faturas**: o `Reajuste de fatura` vai para `faturas.ajuste_centavos`. O que só o geral trouxe vai para a aba nova **Ajustes sem cartão**, onde o dono escolhe o cartão; até lá ele impede gravar. As faturas exportadas (e as dos meses até a última exportada) nascem sem datas. As das parcelas futuras nascem dos dias padrão do cartão, como no app.
- **Fatura importada = paga** (decidido com o dono nesta sessão; termo novo no glossário): o app lê a fatura sem fechamento nem vencimento como `paga`, sem nada a pagar e sem saldo anterior para a seguinte (`faturas.importada`, usada em `cartoes.faturas_do_titular`). Assim o histórico não vira saldo anterior e não ocupa o limite. Efeito aceito pelo dono: a fatura escolhida à mão num cartão sem os dias padrão também conta como paga até ganhar as datas.
- **Pendências**:
  - A fatura que ainda está aberta na virada também chega sem datas (paga). O dono dá as datas a ela antes da tarefa diária rodar, senão as parcelas automáticas seguintes viram realizadas cedo. Ficou no checklist do [ticket 69](69-virada-para-o-app.md).
  - Conferir nos exports reais se há sequências quebradas, parcelas de cartão sem fatura em meses passados (ficam na conta e o parcelamento no cartão), o centavo da divisão nas parcelas geradas e dois reajustes iguais sem cartão no mesmo mês (dividem a escolha). Ficou no [ticket 92](92-rodar-o-importador-nos-exports-reais.md).
  - Gravar de verdade e refazer: [ticket 91](91-importador-do-mobills-gravar-e-refazer.md), com o checklist atualizado pelo que este ticket já fez.

## Notas

- Do [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md): O ajuste de fatura já tem onde ficar: `faturas.ajuste_centavos` (migration `0038`, backup na versão 14), editável por `PATCH /api/cartoes/{id}/faturas/{mes}`; o `Reajuste de fatura` importado grava ali.
- Do [ticket 46](46-parcelamento-criar.md): o backup (versão 16) traz `parcelamentos` (sem coluna de tipo; `valor_total_centavos`, `parcelas`, `data` da compra ou da 1ª parcela, `automatico`, `geradas`), `parcelamento_categorias`, `parcelamento_tags` e, em `lancamentos`, `parcelamento_id` e `parcela`. Para a tarefa diária não gerar de novo, `geradas` = `parcelas`, e o id da parcela gerada pelo importador deve ser `uuid5(parcelamento, número)`, como o do app. No cartão, o parcelamento é sempre automático.
