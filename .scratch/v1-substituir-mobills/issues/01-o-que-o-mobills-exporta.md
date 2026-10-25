# O que o Mobills exporta

Type: research
Status: resolved
Blocked by: 14
Skills: `research` (AFK, em sub-agente)
Modelo recomendado: Sonnet
Effort recomendado: medium
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add2e6b9e6abcd8c135ad24
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Que dados o Mobills deixa exportar, por qual caminho e em que formato?

Levantar:

- onde fica a exportação (app, site) e qual plano do Mobills ela exige;
- os formatos (CSV, XLS, OFX, backup do app) e se há limite de período por exportação;
- os campos de cada coisa exportada: lançamentos (data, valor, descrição, conta, categoria e subcategoria, tags, efetivado ou pendente), transferências, contas e saldos, cartões e faturas (data da compra e fatura em que caiu), parcelas (uma linha por parcela? há vínculo entre elas?), recorrências e planejamento;
- se existe API, backup completo ou outra forma de tirar os dados;
- limitações conhecidas (o que não sai na exportação).

Decisões que esperam por isso: [Categoria única ou só tags](04-categoria-unica-ou-so-tags.md), [Exportar o Mobills e medir o histórico](07-exportar-o-mobills-e-medir-o-historico.md) e a importação do Mobills (ainda no "Not yet specified" do mapa).

## Checklist

- [x] Fontes primárias: central de ajuda e site do Mobills, termos de uso, a própria tela de exportação quando acessível
- [x] Achados num único Markdown, cada afirmação com a fonte, numa branch `research/mobills-exportacao` enviada e sem PR
- [x] Ponteiro para a branch e resumo do achado neste ticket, em `## Answer`

## Answer

Resolvida pela exportação de teste do dono ([ticket 14](14-ler-a-central-de-ajuda-e-exportar-de-teste.md)), sem nenhum dado real aqui. A pesquisa de fontes públicas (parcial) está na branch `research/mobills-exportacao` (commit `e4ef538`, sem PR): a central de ajuda segue bloqueada (403, Cloudflare), então o que vale abaixo vem dos arquivos.

- **Formato e caminho:** XLSX (`.xlsx`), exportado pelo app. Há dois modos: **todas as transações** (qualquer período) e **só cartão de crédito**. O plano exigido não foi confirmado (a conta do dono exporta; ver [ticket 18](18-importacao-do-mobills-cartao-e-datas.md)).
- **Período:** o modo "todas as transações" aceitou 2 meses (jul-ago, 300 linhas) num arquivo só. O limite máximo de período não foi testado (ticket 18).
- **Abas do arquivo de todas as transações:** `Receitas e Despesas` (união, com linha final `Total (receitas - despesas)`), `Despesas`, `Receitas` e `Transferências`. Cada aba de lançamentos termina com uma linha em branco e uma linha de total, que o importador precisa descartar. `Transferências` veio vazia nos arquivos (colunas `Data`, `Conta origem`, `Conta destino`, `Valor`, `Tags`).
- **Arquivo só de cartão:** uma aba, `Despesas`, mesmas colunas.
- **Terceiro modo, descoberto depois: exportação por cartão e por mês (fatura).** Uma aba só (nomeada `Receitas`, apesar de serem despesas), 4 colunas: `Data`, `Descrição`, `Categoria`, `Valor`. O nome do arquivo identifica o cartão (`<cartão>_-_<rótulo>.xlsx`); o cartão e o mês da fatura **não** vêm em nenhuma coluna nem aba. `Data` é texto `dd/mm/aaaa` e é a **data real da compra** (amostra: uma fatura com 87 linhas, de 06/06/2025 a 24/01/2026, em ordem decrescente; as datas antigas são de compras parceladas). `Valor` é **texto** `R$ 228,65`, positivo (duas linhas com sinal negativo, créditos/estornos). Não tem `Conta`, `Situação`, `Subcategoria` nem `Tags`, não tem linha de total e **não tem o sufixo `(n/total)`** nas parcelas: o número da parcela se perde, ficando só a data da compra. Só dá para exportar um mês por vez, então o histórico de N meses e M cartões são N x M arquivos.
- **Colunas de lançamento (8, iguais nos dois modos):** `Data`, `Descrição`, `Valor`, `Conta`, `Situação`, `Categoria`, `Subcategoria`, `Tags`.
- **Tipos:** `Data` é **texto** `dd/mm/aaaa`; `Valor` é número com sinal (despesa negativa, receita positiva), sem moeda; `Situação` só assumiu `Paga` (pendentes não foram vistos); `Categoria` é uma só por lançamento; `Subcategoria` veio **vazia** em todas as linhas; `Tags` é texto livre, uma só por linha nas amostras, separador de várias tags desconhecido; `Conta` foi `Carteira` em todas as linhas, inclusive as de cartão.
- **Cartão não é identificado no arquivo geral:** nenhuma coluna diz que a linha é de cartão. O único jeito de separar é cruzar com o export "só cartão": em setembro, 129 de 146 despesas eram de cartão e o cruzamento por descrição, valor, categoria e tags casou todas, sem sobra do lado do cartão.
- **Data da compra se perde nos dois modos acima:** todas as compras de cartão do mês saem com a **mesma data**, a do vencimento da fatura (setembro: 129 linhas em `30/09`; agosto: `31/08`). A data real da compra não existe no arquivo. O terceiro modo (fatura por cartão e mês, acima) traz a data real.
- **Parcelas:** uma linha por parcela por mês, com o sufixo `(n/total)` na `Descrição` e **sem coluna de vínculo**; reagrupar depende de casar descrição, valor e sequência (76 de 148 despesas de setembro eram parcelas).
- **Ajuste de fatura:** a categoria `Reajuste de fatura` aparece com valores de centavos (-0,01 e -0,03), arredondamento de fatura que o importador deve tratar.
- **Não saem:** contas e saldos, cartões (limite, fechamento, vencimento), faturas como entidade, recorrências, planejamento e categorias sem uso. Só lançamentos.
- **Portabilidade (LGPD):** não é necessária para o que já saiu; reavaliar só se o histórico completo não couber na exportação (ticket 18).

Decisões do [mapa](../map.md) que isto destrava: [Categoria única ou só tags](04-categoria-unica-ou-so-tags.md) e [Exportar o Mobills e medir o histórico](07-exportar-o-mobills-e-medir-o-historico.md). Pendências no [ticket 18](18-importacao-do-mobills-cartao-e-datas.md).
