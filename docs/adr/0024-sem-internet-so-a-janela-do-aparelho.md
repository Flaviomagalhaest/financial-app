---
status: accepted
---

# Sem internet, só a janela do aparelho: 12 meses pelo mês em que conta e todo o futuro

O aparelho deixa de guardar a lista inteira de lançamentos e guarda só a **janela do aparelho**: os lançamentos que contam nos últimos 12 meses, pelo mês em que contam (o da fatura, na compra no cartão), e todos daqui para frente, inclusive os previstos das recorrências até o horizonte. O que fica antes da janela só aparece com internet, e a tela que precisa dele diz isso em vez de esconder. O aparelho relê a janela inteira, comprimida. A medida do ticket 123 mostrou que a lista inteira não aguenta o histórico real: com os 11 mil lançamentos importados do Mobills, o Histórico não terminou de abrir em 5 min num celular simples simulado, e a resposta passa do limite de 6 MiB da Lambda ([pesquisa](../../.scratch/v1-substituir-mobills/research/limites-de-resposta-da-lambda.md)). Quem decidiu foi o dono, no ticket 124.

## Considered Options

- **Lista inteira, comprimida, com o Histórico virtualizado**: com gzip, a resposta cabe até uns 40 mil lançamentos (28 anos ou mais). Mas o custo no aparelho (gravar no IndexedDB, memória, o que cada tela recalcula sobre a lista) cresce uns 1.400 lançamentos por ano, para sempre.
- **As páginas que o Histórico já leu**: o que existe sem internet dependeria de até onde a pessoa rolou, o que é difícil de prever e de explicar.
- **Janela de 3 ou 6 meses**: mais leve, mas deixaria sem internet o estorno de uma compra de meses atrás e o ano que a Evolução compara. Com o Histórico desenhado em partes e a resposta comprimida, 12 meses (uns 1.400 lançamentos, de 150 a 230 KB comprimidos) custam pouco.
- **Janela pela data da compra**: a fatura e o Mês do mês mais antigo da janela ficariam incompletos sem internet.
- **Pedir só o que mudou desde a última leitura**: mais leve que reler a janela, mas pede no servidor um "mudou desde" e o tratamento do que sai da janela quando o mês vira. Fica para quando a medida pedir.

## Consequences

- A [ADR 0011](0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md) continua valendo dentro da janela. Fora dela, abrir, editar, estornar ou ver as parcelas de um lançamento pede internet ("Sem internet: este lançamento não está no aparelho").
- As telas que hoje filtram a lista guardada passam a ler do servidor: as compras da fatura, o Ranking e o "A escolher" do Mês e as parcelas do parcelamento. Sem internet, mostram o que guardaram da última leitura ou dizem que precisam dela.
- A busca sem internet olha só a janela e diz isso.
- O Histórico desenha mês a mês, conforme a pessoa rola. Depois da janela, com internet, continua lendo do servidor sem guardar. Sem internet, o fim da janela diz que é preciso internet para ver antes.
- A API comprime a resposta (gzip), o que também tira o limite de 6 MiB do caminho.
- O aparelho guarda lançamento por lançamento, não a lista num bloco só, e avisa só quem lê a resposta que mudou.
