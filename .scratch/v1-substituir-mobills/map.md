# Mapa: V1 que substitui o Mobills

Label: wayfinder:map

## Destination

Spec da v1 do app de finanças do casal, pronta para `/to-spec` e `/to-tickets`, com as decisões de produto, modelo de dados e arquitetura na AWS tomadas e nenhum código de produção. A v1 substitui o Mobills: cobre os requisitos obrigatórios, a base de contas e cartões, a importação do histórico do Mobills desde 2019 e as funcionalidades complementares listadas em Notes.

## Notes

**Domínio:** finanças pessoais de um casal (Flávio e a esposa). Vocabulário em [GLOSSARY.md](../../GLOSSARY.md); decisões difíceis de reverter em `docs/adr/`.

**Skills por tipo de ticket:**

- `research`: skill `research` (AFK, em sub-agente). Os achados ficam numa branch `research/<nome>`, enviada e nunca mesclada, com um ponteiro no ticket.
- `grilling`: skills `grilling` e `domain-modeling` (HITL).
- `prototype`: skill `prototype` (HITL). O protótipo fica numa branch `prototipo/<nome>`, fora da `main`, com um ponteiro no ticket.
- `task`: o ticket traz o passo a passo; é HITL quando depende do dono.

**Requisitos obrigatórios da v1** (pedido original do dono):

1. Funciona na web, no Android e no iPhone.
2. Registro manual de gastos e receitas do dia a dia, com uma jornada fácil e rápida.
3. Compromissos futuros: parcelas no cartão, dívidas, seguros, salários.
4. Planejamento do mês por item (ex.: R$ 1.000 em alimentação, R$ 650 com carro, R$ 100 com farmácia).
5. Várias tags por lançamento ("trabalho", "saúde", "alimentação", "família").
6. Estatísticas com gráficos e dashboards.
7. Visão do cartão de crédito: uma linha no mês, com as compras e suas tags fáceis de consultar.
8. Roda na AWS com o menor custo possível, com o histórico de dados bem pensado (o casal usa o Mobills desde 2019).

**Base que vem do Mobills:** contas com saldo (corrente, poupança, carteira), transferências e pagamento de fatura como transferência.

**Funcionalidades complementares aceitas na v1:**

- Lançamento: funciona sem internet e sincroniza depois; favoritos e "repetir último"; atalho na tela inicial do celular que abre direto o novo lançamento; sugestão automática de tags pelo histórico da descrição.
- Futuro: parcelamento com antecipação de parcelas e quitação do restante; recorrência com ou sem fim, mudando o valor daqui para frente ou só em um mês, sem mexer no resto; o previsto vira realizado quando acontece, com a lista do que venceu sem confirmação ("contas da semana").
- Planejamento: copiar do mês anterior ou de um modelo padrão; "quanto ainda posso gastar", contando o já gasto e o já previsto; aviso no momento de lançar (ex.: "Alimentação: 82% do planejado").
- Cartão: a compra cai na fatura certa pelos dias de fechamento e vencimento; limite comprometido pelas parcelas futuras; vários cartões e cartão adicional.
- Consulta: fechamento do mês; comparação com o mês anterior, com o mesmo mês do ano passado e ao longo dos anos; busca em todo o histórico com filtros salvos.
- Casal: tag de pessoa e lançamento conjunto (ver o glossário); quem criou e quem alterou por último cada lançamento.
- Dados: projeção do saldo dos próximos meses; exportação de tudo (CSV ou backup).

**Preferências do dono:**

- Dois usuários, sem cadastro público e sem multi-inquilino, nem como objetivo futuro.
- Sem data fixa: a v1 está pronta quando der para largar o Mobills; a spec pode fatiar a v1 em etapas.
- Loja de apps não é requisito: basta ícone na tela inicial e boa experiência no celular.
- Backend em Python, para abrir caminho a cálculos de ciência de dados no futuro. O dono já usa Expo em outro repositório.
- Conta AWS nova, filha de uma conta de governança (AWS Organizations), no free tier com US$ 120 de crédito.
- Custo-alvo de US$ 0 a 1 por mês no uso normal, com teto de US$ 5 e alerta de orçamento na AWS.
- Sem domínio próprio: o endereço padrão da AWS basta para dois usuários.
- Os dados reais do Mobills nunca entram no repositório; os tickets guardam só contagens e a forma dos dados.

## Decisions so far

## Not yet specified

- **Sincronização offline e conflitos:** como um lançamento feito sem internet chega ao servidor e o que acontece quando os dois editam o mesmo lançamento. Depende da plataforma e do banco.
- **Importação do Mobills:** como as categorias, tags, contas, cartões, faturas e parcelas de lá viram os conceitos daqui, e como é o dia da virada (onde se lança durante a transição).
- **Projeção de saldo:** a regra que junta saldo atual, previstos e planejamento, mês a mês.
- **Planejamento com várias tags:** sobre o que um item planejado incide e como "quanto ainda posso gastar" conta um lançamento com mais de uma tag.
- **Sugestão automática de tags:** de onde vem a sugestão e como ela aprende com o uso.
- **Limite comprometido do cartão:** como mostrar quanto do limite as parcelas futuras ocupam.
- **Busca e filtros salvos:** o que se busca e o que um filtro salvo guarda.
- **Exportação:** formato e conteúdo do CSV e do backup.

## Out of scope

- Importar extrato ou fatura (OFX/CSV) e Open Finance: na v1 o lançamento é manual.
- Conferência da fatura em lote a partir do arquivo da fatura: o dono já prevê essa funcionalidade para depois da v1.
- Leitura do QR code da nota fiscal (NFC-e), foto de recibo e anexo de comprovante: automação de entrada fica para depois da v1.
- Lançamento por voz ou texto livre com IA: idem.
- Metas e caixinhas; patrimônio e investimentos: não servem para largar o Mobills.
- Comparações corrigidas pela inflação (IPCA): idem.
- Notificações (fatura fechando, planejamento estourando): idem.
- Divisão de despesas do casal ("quem deve a quem"): a tag de pessoa já diz de quem é cada lançamento.
- Dividir um lançamento em partes com tags diferentes: o dono não quer se preocupar com isso agora.
- Dívida com juros calculada pelo app (tabela Price ou SAC): dívidas entram como parcelamento ou recorrência, com os valores já conhecidos.
- Sobra do planejamento que passa para o mês seguinte (envelope acumulado): fica para depois da v1.
- Histórico completo de alterações de um lançamento: na v1 basta saber quem criou e quem alterou por último.
