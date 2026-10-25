# Protótipo do ticket 11: Dashboards e fechamento do mês

PROTÓTIPO DESCARTÁVEL. Fica só na branch `prototipo/dashboards`, nunca entra na `main`.

Pergunta: quais visões a v1 mostra, e como?

Abrir: dê dois cliques em `dashboards.html` (ou `python3 -m http.server` nesta pasta e abra `/dashboards.html`).
Troque de variação pela barra preta no rodapé, pelas setas ← → do teclado ou pelo endereço (`#A`, `#B`, `#C`).

- **A: Painel do mês.** Uma página só, rolando: fechamento (meses passados), resumo, planejamento item a item, "a escolher", cartões numa linha que abre as compras, "para onde foi" por categoria, tag ou pessoa, comparação com o mês anterior e com o mesmo mês do ano passado, 12 meses, anos e projeção de saldo.
- **B: App com abas.** Hoje (quanto ainda dá para gastar, a escolher, atrasados, fatura), Mês (fechamento em texto corrido, itens, ranking com lançamentos numa folha que sobe), Cartões, Histórico (uma métrica por vez: 12 meses, anos ou outubro de cada ano) e Futuro (projeção).
- **C: Planilha do ano.** Categorias, tags, pessoas ou cartões nas linhas, 12 meses mais 3 futuros nas colunas (ou os anos de 2019 a 2026), células coloridas contra o planejado, clique na célula para ver os lançamentos.

A e B têm o **experimento da pizza por natureza do gasto** (Essencial, Estilo de vida, Projetos), um grupo exclusivo por lançamento, para o casal dizer se a pizza faz falta. C não tem pizza nenhuma.

Dados 100% fictícios, gerados no próprio arquivo com semente fixa; "hoje" é 25/10/2026. Nada é salvo: as escolhas de "a escolher" somem ao recarregar.

## O que observar

1. Qual variação (ou que mistura: "o topo do B com a planilha do C") vocês abririam todo dia? E no fim do mês?
2. A pizza por natureza fez falta, ou as barras bastam?
3. O cartão numa linha que abre as compras resolve a consulta da fatura?
4. O fechamento como número grande (A), como texto (B) ou como coluna (C)?
5. Na projeção de saldo: a linha "só com os previstos" ou a "previstos + planejamento"? (a regra está em aberto no mapa)
6. Faltou alguma visão do Mobills que vocês usam?
