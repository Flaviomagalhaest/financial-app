# Importação do Mobills: separar o cartão, recuperar a data da compra e fechar as lacunas da exportação

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono); apoio: `research` para a parte da central de ajuda
Modelo recomendado: Opus
Effort recomendado: high
Issue: #36
Origem: exportação de teste do [ticket 14](14-ler-a-central-de-ajuda-e-exportar-de-teste.md); achados no `## Answer` de [O que o Mobills exporta](01-o-que-o-mobills-exporta.md); ponto "Importação do Mobills" do "Not yet specified" do [mapa](../map.md)

## Question

Como a importação do Mobills traz o cartão com a data certa da compra e o histórico completo, dado o que a exportação entrega?

Observações do dono sobre os arquivos de teste:

- O export de todas as transações não diz o que é cartão; talvez a importação precise de **dois exports** (cartão e pagamentos/compras gerais), cruzados para separar.
- As compras do cartão saem todas na data do vencimento da fatura. O dono quer a **data certa da compra**, principalmente nas parceladas e nas faturas do mês vigente; para faturas antigas não é preciso. Isso pede um input manual das datas.

Decidir:

- importar com dois arquivos e cruzar (descrição, valor, categoria, tags) para marcar o cartão, ou outro caminho; o que fazer com a linha ambígua (compra igual, mesmo valor);
- como e quando o dono informa a data da compra: parceladas ativas e fatura do mês vigente (tela de revisão pós-importação? planilha de datas?), e o que vale para o resto (data do vencimento da fatura, como na [ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md): o mês contado é o da fatura, então a data da compra não muda o mês);
- como reagrupar as parcelas `(n/total)` em parcelamentos ([ADR 0004](../../../docs/adr/0004-previsto-e-situacao-do-lancamento.md)) sem coluna de vínculo, e o que fazer com parcelas futuras que o export não traz;
- como é o de-para de categorias e tags decidido no [ticket 04](04-categoria-unica-ou-so-tags.md) (cada nome de `Categoria` e de `Tags` do Mobills vira categoria, tag ou é descartado; padrão: mesmo nome e mesmo papel; já decidido: "viagem" e "ilhabela" viram a categoria Viagem, "novo ap" continua tag): tela de revisão ou planilha, e quando o dono revisa;
- como tratar `Reajuste de fatura` (centavos), `Conta = Carteira` em tudo (contas e cartões não saem), `Situação` só `Paga` e a linha de total/linha em branco no fim de cada aba.

## Checklist

- [x] Dono lê a central de ajuda (`https://ajuda.mobills.com.br`, navegador) e informa: o plano exigido para exportar, o limite de período por exportação e se há backup completo ou exportação de contas e cartões (feito pela pesquisa, sem o dono: ver `## Answer`)
- [x] Dono exporta o histórico completo (todas as transações e só cartão), por trechos se houver limite, fora do repositório; o [ticket 07](07-exportar-o-mobills-e-medir-o-historico.md) mede
- [x] Dono diz quantos cartões tem (ativos e antigos) e até que mês quer a data real da compra, para fixar quantas exportações por fatura valem o esforço (exportou todas as faturas de todos os cartões, medidas no ticket 07)
- [x] Dono confirma quantos cartões tem: **7 cartões distintos**, os cartões 6 e 7 são novos (por isso poucas faturas)
- [x] Rótulo `AAAAMM` da fatura: a compra de 2026-10-04 no arquivo 202609 era uma transação de R$ 0,02 (ajuste de fatura), que o dono mandou desconsiderar; o cruzamento mostra que o rótulo é o mesmo mês do geral (deslocamento 0)
- [x] Dono roda o `cruzar-historico` (script local, não versionado, saída só de contagens) e cola o resultado, e o agente grava aqui o que o cruzamento mostrou: o dono cruza, localmente, as compras de cartão do export geral com as faturas, para saber se as faturas cobrem todo o cartão do geral (cerca de 4.742 contra 5.967 despesas) e o que sobra no geral sem fatura
- [x] Se a exportação não bastar para o histórico, avaliar o pedido de portabilidade pela LGPD ao encarregado de dados do Mobills (não é necessária)
- [x] Decisão sobre os pontos acima registrada em `## Answer`
- [x] `GLOSSARY.md` atualizado (termos: data da compra x data da fatura, se ainda não estiverem) e o ponto "Importação do Mobills" do mapa movido para "Decisions so far"

## Answer

O histórico entra pelo **cruzamento do export geral com as faturas por cartão e mês**, numa importação que pode ser refeita até a **virada**, e não mexe no saldo ([ADR 0007](../../../docs/adr/0007-historico-do-mobills-cruzado-e-sem-saldo.md)). Ninguém digita data de compra. Termos novos no [glossário](../../../GLOSSARY.md): **Virada**, **Data da compra**, **Ajuste de fatura** e **Saldo de abertura**.

**Central de ajuda** (pesquisa na branch `research/mobills-central-de-ajuda`, commit `3c15248`, sem PR; as páginas seguem com 403 da Cloudflare, mas a API pública de artigos do Zendesk respondeu): a central não diz que plano exporta (a conta do dono exporta, então não importa); na web, anos anteriores saem "de 2 em 2 anos", com pendentes e efetivadas; no celular saem só efetivadas, sem pendentes e sem transferências; não há backup em arquivo, API nem exportação de contas, cartões, recorrências ou planejamento. Os modos "só cartão" e "fatura por mês" não aparecem na central. A portabilidade pela LGPD não é necessária.

**Fonte e cruzamento**

- Cada linha de fatura casa com o seu par no geral por mês, descrição sem `(n/total)`, valor e categoria. A compra entra **uma vez só**: data da compra e cartão vêm da fatura; `(n/total)`, tags e situação vêm do geral.
- Linhas com a mesma chave no mesmo mês casam na ordem (fatura pela data da compra, geral pela posição); se as do geral tiverem tags ou situação diferentes, o grupo vai para a revisão; a sobra de contagem vira linha sem par.
- Casou em tudo menos na categoria (11 casos): vale a categoria do geral, listada no relatório. Casou só pelo valor (2 casos): vai para a revisão como par provável.
- O que sobra: no mesmo mês, uma linha de fatura e uma do geral sem par e com o mesmo valor viram **par provável** na revisão, que o dono confirma ou separa. A fatura que continuar sem par entra como compra do cartão só com o que a fatura tem (realizada, sem tags). O geral que continuar sem par entra como débito na conta, na data do geral.

**Contas, cartões, faturas e saldo**

- O Mobills tinha **uma conta só** (o débito) e 7 cartões; nada disso sai no export. O dono cadastra a conta e os 7 cartões antes de importar e liga cada pasta de fatura a um cartão. Os **5 inativos ficam arquivados** (fora das opções de novo lançamento, histórico mantido), com fechamento e vencimento opcionais; os 2 ativos têm os dias preenchidos.
- O que não é cartão entra na conta real. O saldo dela parte de um **saldo de abertura** que o dono informa quando quiser; o histórico importado não mexe no saldo e serve às estatísticas, ao planejamento e às comparações.
- Cada fatura importada nasce com o mês da fatura igual ao rótulo `AAAAMM` do arquivo (o mesmo mês do geral, pelo cruzamento), **fechada e paga**, sem datas de fechamento e vencimento e sem pagamento de fatura.
- Investimentos continuam fora da v1; o dono prevê lançá-los depois, a partir de planilhas próprias (anotado no mapa).

**Linhas especiais**

- `Reajuste de fatura` não vira lançamento: vira o **ajuste de fatura** da fatura em que aparece, que conta nos totais e fica fora das categorias, tags e itens do planejamento. O mesmo conceito vale depois da virada ([ADR 0008](../../../docs/adr/0008-ajuste-de-fatura-fica-na-fatura.md)).
- A linha em branco e a linha de total de cada aba são descartadas. `Paga` vira realizado e `Pendente` vira previsto.
- Pendentes que não são parcela (as ocorrências das recorrências do Mobills, sem a regra): os do mês do export e anteriores são **descartados** (o mês corrente do Mobills pode não estar atualizado); os de meses seguintes entram como **previstos avulsos**. Depois da virada, o dono cadastra as recorrências no app e apaga os avulsos que elas substituem.
- Tudo entra como **conjunto** (sem pessoa), com autoria "importado do Mobills".

**Parcelas**

- Um parcelamento junta as linhas do geral com a mesma descrição base, o mesmo valor (tolerância de 1 centavo), o mesmo `total` e números `n` em meses consecutivos. Sequência quebrada (falta um `n`, dois `3/10` no mesmo mês) vai para a revisão.
- As parcelas que o export não trouxe são geradas pela regra do parcelamento: as futuras como previstas; as anteriores ao histórico não entram.
- Parcela futura (sem fatura) herda o cartão, a data da compra e as categorias das parcelas já casadas do mesmo parcelamento e cai na fatura do cartão no mês dela. Parcelamento sem nenhuma parcela casada vai para a revisão, onde o dono escolhe o cartão.

**De-para, revisão e conferência**

- O importador é um **script do backend** rodado localmente pelo dono; os dados nunca entram no repositório. Ele gera uma **planilha de revisão** com:
  - o **de-para** de cada nome de `Categoria` e de `Tags` (despesa e receita separadas), com a contagem e o papel proposto (padrão: mesmo nome e mesmo papel; "viagem" e "ilhabela" viram a categoria Viagem; "novo ap" continua tag; tag que for de pessoa vira pessoa);
  - os pares prováveis, os grupos ambíguos, as sequências de parcela quebradas e os parcelamentos sem cartão;
  - a aba **Conferência**: uma linha por mês, de 2019-02 à virada, com receitas, despesas e ajustes de fatura no mês da fatura, uma coluna **Mobills** que o dono preenche com o total do Mobills, a **diferença** e o **por quê** (linhas de fatura sem par acrescentadas, avulsos descartados, pares prováveis abertos);
  - a aba **Faturas**: o total de cada fatura (cartão e mês), para comparar com a tela de faturas do Mobills.
- O dono edita a planilha e roda de novo, quantas vezes quiser. Depois da virada, as categorias e tags se acertam no app: renomear, juntar e arquivar ([ADR 0006](../../../docs/adr/0006-varias-categorias-e-um-item-do-planejamento.md)) e a **edição em lote** a partir da busca (anotada no ponto "Busca e filtros salvos" do mapa).

**Virada**

- Até a virada, o casal lança no Mobills e a importação pode ser refeita: ela apaga só o que veio do Mobills e importa de novo.
- No dia da virada: param de lançar no Mobills, exportam o geral **pela web** e as faturas que faltam, **incluindo a aberta** (é ela que dá a data real da compra na fatura vigente), rodam a importação final, conferem e informam o saldo de abertura. Daí em diante, tudo só no app.

## Comments

- O dono achou um terceiro modo: **exportar a fatura de cada cartão, mês a mês**, que traz a data real da compra e identifica o cartão (pelo nome do arquivo), mas perde `Tags`, `Situação`, `Conta` e o sufixo de parcela `(n/total)` (detalhes no `## Answer` do [ticket 01](01-o-que-o-mobills-exporta.md)). Isso muda a decisão: em vez de pedir a data à mão, a importação pode juntar o export geral (tags, parcelas `n/total`, não-cartão) com as faturas mensais (data da compra, cartão), cruzando por descrição, valor e categoria. O custo é um arquivo por cartão e por mês; a decisão é até quantos meses vale exportar assim (por exemplo só as parceladas ativas e o ano corrente) e o que fazer com o restante (data do vencimento da fatura).
- Medição do histórico no [ticket 07](07-exportar-o-mobills-e-medir-o-historico.md): 6.283 lançamentos no geral (**1 conta só**, 0 subcategorias, 4 tags, 311 `Pendente`) e 4.742 compras em 219 faturas de 7 pastas de cartão. Duas decisões novas: (1) o geral tem uma conta só, então **contas e cartões não vêm da exportação** (o dono cadastra); o cartão vem do nome da pasta das faturas; (2) compra parcelada reaparece em cada fatura sem o número da parcela (hipótese), então reagrupar parcelas das faturas exige agrupar por data da compra, descrição e valor, e o `(n/total)` vem só do geral. Casos estranhos já medidos para o importador: faturas fora de ordem de data (204 linhas), linhas idênticas legítimas (compra repetida no mesmo dia) e estornos negativos nas faturas.
- **Cruzamento do geral com as faturas** (feito pelo dono com `cruzar-historico`, saída só de contagens; 6.283 linhas do geral e 4.742 de faturas): o rótulo `AAAAMM` da fatura é **o mesmo mês** em que o geral lança a compra (deslocamento 0 casou 4.631 das 4.742 linhas, contra 1.611 com -1 e 1.705 com +1). Casamento por mês, descrição sem o `(n/total)`, valor e categoria: **4.618 exatos**, 11 só sem a categoria e 2 só pelo valor, ou **97,7%** das linhas de fatura têm par no geral. **111 linhas de fatura (2,3%) sem par** (2020: 2, 2022: 19, 2023: 13, 2024: 14, 2025: 37, 2026: 26): a causa não foi diagnosticada (descrição editada depois, estorno ou ajuste são hipóteses). Do lado do geral, **443 lançamentos** no último dia do mês ou com `(n/total)` ficaram sem fatura (253 em 2026, 318 com `(n/total)`): o excesso de 2026 combina com parcelas futuras, que ainda não têm fatura; os de 2019 a 2025 (190) podem ser outras despesas no último dia do mês, sem diagnóstico. Dos 2.184 lançamentos do geral no último dia do mês, só uma parte é cartão.
- **Direção possível para a decisão** (a decidir com o dono): usar o cruzamento (mês, descrição, valor, categoria) para juntar cada linha de fatura ao seu par no geral e importar **uma vez só**, com a data real da compra e o cartão da fatura e o `(n/total)`, as tags e a situação vindos do geral; linhas de fatura sem par entram só com o que a fatura tem; lançamentos futuros do geral (pendentes) entram como previstos, sem fatura. Isso elimina o input manual de datas que o dono previa, para o histórico inteiro, e deixa 111 linhas e os candidatos sem fatura para revisão.
