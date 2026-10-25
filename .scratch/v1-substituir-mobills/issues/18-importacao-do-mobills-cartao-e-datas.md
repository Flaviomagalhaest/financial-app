# Importação do Mobills: separar o cartão, recuperar a data da compra e fechar as lacunas da exportação

Type: grilling
Status: ready-for-human
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

- [ ] Dono lê a central de ajuda (`https://ajuda.mobills.com.br`, navegador) e informa: o plano exigido para exportar, o limite de período por exportação e se há backup completo ou exportação de contas e cartões
- [ ] Dono exporta o histórico completo (todas as transações e só cartão), por trechos se houver limite, fora do repositório; o [ticket 07](07-exportar-o-mobills-e-medir-o-historico.md) mede
- [ ] Se a exportação não bastar para o histórico, avaliar o pedido de portabilidade pela LGPD ao encarregado de dados do Mobills
- [ ] Decisão sobre os pontos acima registrada em `## Answer`
- [ ] `GLOSSARY.md` atualizado (termos: data da compra x data da fatura, se ainda não estiverem) e o ponto "Importação do Mobills" do mapa movido para "Decisions so far"
