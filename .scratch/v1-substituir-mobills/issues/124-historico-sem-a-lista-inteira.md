# Histórico sem a lista inteira: páginas, janela de meses ou virtualização

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: a decisão é do dono e mexe no ADR 0011); apoio: `research` (limites de resposta da Lambda e da HTTP API), `prototype` se a escolha pedir ver a tela
Modelo recomendado: Opus
Effort recomendado: high
Issue: #287
Origem: [ticket 123](123-historico-com-o-volume-real.md) (31/10). A medida mostrou que o app não aguenta o histórico real.

## A pergunta

O app lê a lista inteira de lançamentos (`GET /api/lancamentos`, sem página), guarda ela inteira no IndexedDB para funcionar sem internet ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)) e o Histórico desenha todos os itens. Com o histórico do Mobills (cerca de 11 mil lançamentos, [ticket 07](07-exportar-o-mobills-e-medir-o-historico.md)) isso não funciona. Qual caminho seguir?

## Os números (ticket 123)

Medidos com `web/e2e/medir-historico.ts`: recarregar o Histórico com a lista já guardada até ele mostrar um lançamento novo, CPU do Chromium 4x mais lenta (celular simples), mediana de 2 rodadas.

| Lançamentos | Resposta da lista | Servidor (fora do navegador) | Até mostrar |
|---|---|---|---|
| 1.600 | 1,1 MB | 0,1 s | 4,8 s |
| 3.000 | 2,0 MB | 0,2 s | 8,2 s |
| 6.000 | 4,0 MB | 0,25 s | 16,5 s |
| 11.000 | 7,3 MB | 0,5 s | mais de 5 min (não terminou); com a CPU sem lentidão, 6,3 a 6,9 s |

- **Cresce em linha reta**, uns 2,5 ms por lançamento no celular simulado. Não há gargalo isolado para tirar.
- **Onde vai o tempo** (trace e perfil de CPU, 6 mil lançamentos): a thread da tela fica ocupada o tempo todo. O React desenha e aplica a lista inteira (8 a 9 s de JS, metade disso em render e commit de 6 mil itens), mais 3 a 4,5 s de layout, 1 a 2 s de estilo, 0,6 a 1,5 s de pintura e 1 a 2 s de GC. A gravação no IndexedDB leva de 1,5 a 3,5 s até o commit. A leitura no servidor e o JSON são pequenos.
- **A resposta passa do limite da Lambda.** Cada lançamento ocupa uns 700 bytes no JSON. O histórico real dá 7,3 MB, e a resposta síncrona da Lambda aceita até 6 MB (conferir com `research`: a API é HTTP API + Lambda, sem compressão na resposta). O limite chega perto de 8.500 lançamentos, e o casal soma uns 1.400 por ano.
- **Releitura em cascata** (achado à parte): cada escrita no IndexedDB avisa todos os ouvintes (`ouvirMudancas`, `web/src/dados/armazem.ts`), e cada hook relê a resposta dele inteira. Uma abertura do Histórico lia a lista guardada **54 vezes**. Avisar só quem lê a resposta que mudou baixou para 6, mas o tempo até mostrar quase não mudou (4,8 → 4,2 s com 1.600; 16,5 → 17,7 s com 6 mil, dentro do ruído). A mudança foi desfeita: vale fazer junto com o caminho escolhido, não sozinha.
- **Os testes pesam também**: o `getByRole(...).filter(...)` do Playwright percorre a árvore de acessibilidade dos milhares de itens a cada tentativa, o que deixa a espera do teste mais lenta que a da pessoa. Com o banco local de duas suítes, isso também conta nos 5 s.

## Caminhos

1. **Lista em páginas** (do mais novo para trás, "carregar mais"), como já faz a busca (`POST /api/busca`). Resolve o tamanho, a gravação e o render. Sem internet, o aparelho só tem as páginas já lidas: reabre o ADR 0011 (o que a busca e a sugestão sem internet enxergam).
2. **Janela de meses**: o aparelho lê e guarda só os últimos N meses (o resto pela busca, com internet). Parecido com as páginas, mas o limite é o tempo, que combina com "Mês" e "Hoje". Também reabre o ADR 0011.
3. **Virtualização** (só desenhar o que está na tela). Tira o render e o layout (a maior parte do tempo), mas a lista continua inteira: o limite de 6 MB da Lambda e a gravação no IndexedDB continuam. Sozinha não basta.
4. **Combinação**: 1 ou 2 para o tamanho, com 3 se a página ficar grande.

## Checklist

- [x] Dono escolhe o caminho (e, na janela, quantos meses; nas páginas, o tamanho)
- [x] Decidir o que o aparelho guarda sem internet e registrar no ADR 0011 (ou ADR novo)
- [x] Confirmar com `research` o limite de resposta da Lambda e da HTTP API e se comprimir a resposta ajuda
- [x] Abrir os tickets de implementação, com a releitura em cascata e a volta do prazo do teste "a rede volta, mas a lista não chega antes do envio" (`web/e2e/sem-internet.spec.ts`, `lerAListaInteira`) ao padrão

## Answer

Decidido pelo dono em 02 e 03/11, em três rodadas de `grilling` (Q1 a Q12, todas com a recomendação aceita). Registro: [ADR 0024](../../../docs/adr/0024-sem-internet-so-a-janela-do-aparelho.md), uma linha nas Consequences do [ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md) e o termo **Janela do aparelho** no `GLOSSARY.md`.

- **Q1, caminho**: janela de meses (caminho 2). O aparelho deixa de guardar a lista inteira.
- **Q2**: guardar lançamento por lançamento, avisar só quem lê a resposta que mudou e um GET da lista por tela entram em qualquer caminho.
- **Q3, tamanho**: 12 meses (uns 1.400 lançamentos, de 150 a 230 KB comprimidos).
- **Q4, o que entra**: pelo mês em que o lançamento conta (o da fatura, na compra no cartão), mais todo o futuro (parcelas e previstos das recorrências até o horizonte de 24 meses).
- **Q5, Histórico**: desenhado mês a mês ao rolar; depois da janela, com internet, continua pelo servidor sem guardar; sem internet, o fim da janela diz que é preciso internet.
- **Q6, fora da janela sem internet**: a tela avisa, não esconde. Abrir, editar, estornar e ver as parcelas pedem internet; as compras da fatura, o Ranking e o "A escolher" do Mês e as parcelas passam a ler do servidor; a busca sem internet diz que olhou só os 12 meses.
- **Q7, atualização**: reler a janela inteira, comprimida. "Mudou desde" só se a medida pedir.
- **Q8**: comprimir a resposta da API (gzip na FastAPI), em ticket próprio.
- **Q9**: o termo é **Janela do aparelho**.
- **Q10**: ADR novo (0024), com uma linha no 0011.
- **Q11**: sem protótipo: a tela é a lista de hoje com cabeçalho de mês e o aviso do fim da janela, e o ticket 167 a mostra pronta com `run`.
- **Q12, tickets**: [163](163-comprimir-a-resposta-da-api.md) (gzip), [164](164-guardar-lancamento-por-lancamento-e-reler-so-o-que-mudou.md) (armazenamento por item e releitura), [165](165-telas-que-filtram-a-lista-leem-do-servidor.md) (telas que filtram a lista leem do servidor), [166](166-janela-do-aparelho.md) (a janela, bloqueado por 164 e 165) e [167](167-historico-desenhado-mes-a-mes.md) (Histórico mês a mês, bloqueado por 166).

**Pesquisa** ([limites de resposta da Lambda](../research/limites-de-resposta-da-lambda.md)): a resposta síncrona da Lambda é de 6 MiB e conta o envelope serializado (uns 12% maior que a lista), então o teto sem compressão fica perto de 7.900 lançamentos, não 8.500. Com gzip na API, cabem de 40 a 63 mil. A HTTP API e o CloudFront não comprimem a resposta da API, e a HTTP API não tem streaming. Falta conferir no `dev` com `curl` que o gzip passa pela HTTP API (no ticket 163).
