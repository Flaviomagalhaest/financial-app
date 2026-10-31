# Histórico sem a lista inteira: páginas, janela de meses ou virtualização

Type: grilling
Status: ready-for-human
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

- [ ] Dono escolhe o caminho (e, na janela, quantos meses; nas páginas, o tamanho)
- [ ] Decidir o que o aparelho guarda sem internet e registrar no ADR 0011 (ou ADR novo)
- [ ] Confirmar com `research` o limite de resposta da Lambda e da HTTP API e se comprimir a resposta ajuda
- [ ] Abrir os tickets de implementação, com a releitura em cascata e a volta do prazo do teste "a rede volta, mas a lista não chega antes do envio" (`web/e2e/sem-internet.spec.ts`, `lerAListaInteira`) ao padrão
