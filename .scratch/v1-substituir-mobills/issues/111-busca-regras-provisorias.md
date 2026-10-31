# Busca: conferir as regras provisórias

Type: grilling
Status: ready-for-human
Blocked by: 59
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se uma regra mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #229
Origem: [ticket 59](59-busca.md): a spec, o [ticket 24](24-busca-e-filtros-salvos.md) e o [ADR 0013](../../../docs/adr/0013-busca-por-data-da-compra-e-fatura-a-parte.md) não dizem o que fazer nestes casos, e a implementação escolheu um comportamento provisório para cada um (em `backend/app/busca.py`, com teste em `backend/tests/test_busca.py`, e na tela em `web/src/busca/`); a revisão do 59 apontou os itens 2 a 5

## As perguntas

1. **Filtro Fatura sem cartão.** A spec fala em "fatura (cartão e mês da fatura)". Sem cartão, o filtro vale como o mês em que cada lançamento conta (o da fatura no cartão, o da data no resto), como a aba Mês; é o que o atalho "Ver os lançamentos" do ranking do Mês usa, porque a linha do ranking mistura contas e cartões. A ficha diz "Conta em 11/2026". Fica assim, ou o atalho do Mês deveria abrir outra coisa?
2. **Parcelamento com filtro de situação.** Os filtros valem parcela a parcela; a linha do parcelamento mostra a soma das parcelas achadas (com "4 das 10 parcelas na busca"), e o filtro de valor olha essa soma. Sem filtro de situação, é o total. A spec diz "a compra parcelada conta pelo valor total, uma vez … o filtro de valor segue a mesma regra". Com `Previsto` marcado, a linha deveria mostrar o total da compra mesmo assim?
3. **Realizado e previsto de um parcelamento nos totais.** Cada parcela conta na situação dela: uma geladeira de R$ 2.500,00 em 10x comprada ontem põe R$ 250,00 em "Despesas" e R$ 2.250,00 em "Previstos à parte", embora a linha mostre R$ 2.500,00. A soma bate, mas o casal pode estranhar.
4. **Atalho do Mês e os números.** O ranking do Mês soma o realizado e o previsto de cada linha; a busca mostra o realizado em "Despesas" e o previsto à parte, então só a soma das duas bate com a linha do ranking. Mostrar também um "total com previstos" no topo?
5. **Estorno no filtro de valor e na ordem "Maior valor".** O estorno avulso (sem a compra no resultado) entra pelo valor dele, positivo: um estorno de R$ 500,00 aparece entre os maiores. Os totais já o descontam (ADR 0016). Ordenar e filtrar pelo valor com sinal?
6. **Transferências.** Aparecem sem filtro de tipo, numa linha própria, fora dos totais e da contagem ("Lançamentos" no topo não as conta). O pagamento de fatura só aparece com o tipo Transferência. Elas não têm tag nem pessoa: o filtro de tag as tira (salvo "Sem tag"), o de pessoa também (salvo "Conjunto"), e o filtro Fatura só acha o pagamento daquela fatura.
7. **Conta e cartão num filtro só.** A spec lista "conta" e "cartão" à parte; como entre filtros é E, os dois juntos não achariam nada. A implementação junta os dois num filtro "Conta ou cartão" (OU). O cartão titular não traz as compras do adicional nesse filtro (só no filtro Fatura).
8. **Ajuste de fatura e saldo anterior.** Não são lançamentos e ficam fora da busca: no filtro Fatura, o total da busca é o das compras, e pode diferir do total da fatura e das despesas do mês quando há ajuste.
9. **Valores iniciais.** `buscaPorPagina` = 50 linhas por página (`config/valores-iniciais.json`) e a espera de 300 ms depois de parar de digitar antes de buscar (`web/src/busca/TelaDaBusca.tsx`).
10. **Sem internet.** O aparelho guarda a lista inteira dos lançamentos (`/api/lancamentos`), não só os recentes, então o resultado parcial costuma ser quase completo; ficam de fora as transferências, que o aparelho não guarda. O aviso diz "Resultado parcial, sem internet: só o que este aparelho guarda."
11. **Lupa e aba.** A lupa (🔍) fica no topo, ao lado de Configurações, e abre `#/busca`, que marca a aba Histórico; a lista do Histórico (`#/historico`, editar e excluir) continua como estava até o [ticket 57](57-aba-historico.md).

## Checklist

- [ ] O dono responde cada pergunta e a resposta vai para `## Answer`
- [ ] Se uma regra mudar: teste de API em `backend/tests/test_busca.py`, ajuste em `backend/app/busca.py` e na busca do aparelho (`web/src/dados/busca.ts`), e o README (seção Busca) acompanha
