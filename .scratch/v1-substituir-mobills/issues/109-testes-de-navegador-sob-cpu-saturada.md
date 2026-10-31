# Testes de navegador que ainda falham sob CPU saturada

Type: task
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #233
Origem: [ticket 90](90-teste-do-recusado-intermitente.md): com 2 a 4 laços de CPU ocupando os 4 núcleos e `--repeat-each`, sobraram falhas que não aparecem na máquina livre (suíte inteira 106 de 106, banco limpo).

- `e2e/sem-internet.spec.ts` › "criado com a resposta perdida e depois editado ou excluído sem internet": o link "Editar" fica "not stable" (a lista reordena enquanto o `sync` reenvia a fila) ou "Salvar" fica desativado. Hipótese do 90 ainda de pé: o reenvio da fila disputa com o `setOffline(true)` do teste.
- `e2e/sem-internet.spec.ts` › "sem internet, as telas abertas...": "Salvar" desativado dentro de `lancar` (cadastro ainda não carregado na tela).
- `e2e/sem-internet.spec.ts` › "o saldo da conta conta os não enviados do aparelho...": falhou uma vez num `toContainText` do saldo na suíte inteira com o Postgres local cheio de rodadas (ticket 96), e passou 4 de 4 sozinho; o diff do 96 não mexe no saldo.
- Aviso para quem escreve teste: ao abrir a Hoje, o `nao-enviados` começa vazio até a fila ser lida do IndexedDB, então `toHaveCount(0)` logo depois de trocar de aba não prova que a fila subiu (ticket 96: os testes da recorrência perguntam ao servidor).

## Checklist

- [x] Reproduzir com laços de CPU e `--repeat-each`: 4 laços em 4 núcleos e até 8 laços não reproduziram (54 de 54 passaram). Reproduz com tudo preso a um núcleo: `taskset -c 0` na suíte e em 4 laços `sh -c 'while :; do :; done'`
- [x] Esperar no teste o sinal real antes do próximo passo: a edição espera o `valor` da tela (`sem-internet.spec.ts`, "resposta perdida" e "saldo da conta")
- [x] Suíte sob carga sem falha (`sem-internet.spec.ts` 13 de 13 com um núcleo e 4 laços); PR aberto para `main`

## Diagnóstico

- "resposta perdida e depois editado": falhava 3 de 6. O teste clicava "9" antes de `TelaDeLancamento` hidratar da lista guardada; a hidratação apagava o dígito e "Salvar" gravava R$ 0,01. Não era disputa com o `sync` (`marcarSemResposta` relê o item na transação). O mesmo padrão estava no teste do saldo. Pendência de produto: [ticket 124](124-edicao-descarta-digito-antes-de-carregar.md).
- "edita e exclui sem internet" (esperar `nao-enviados` zerar) e os outros: não eram lógica quebrada; sob um núcleo disputado cada teste levava 30 a 37 s contra 5 s livre, e os limites padrão (5 s por espera, 30 s por teste) estouravam. `playwright.config.ts` agora tem `timeout: 90_000` e `expect.timeout: 20_000`.
- "Salvar desativado dentro de `lancar`" e o `toContainText` do saldo não reapareceram nas rodadas; ficam cobertos pelos limites maiores e pelo sinal do `valor`. Reabra se voltarem.

## Notas

- Os testes do ticket 90 só são confiáveis com o banco limpo: o Postgres local acumula lançamentos entre rodadas (871 numa) e a suíte fica 3x mais lenta, com falhas de `toBeVisible` em `cadastrar`. Recrie o banco entre rodadas longas. O ticket 98 viu o mecanismo: com o banco cheio, cada abertura lê as faturas de todos os cartões acumulados, e o envio da fila (trava exclusiva) espera atrás dessas leituras (travas compartilhadas, cada uma com até 10 s de tempo limite). Numa rodada, 3 s depois de "Salvar" havia 6 travas compartilhadas presas e nenhum lote tinha saído.
- Servidores do `webServer` que ficam de pé depois de uma rodada interrompida são reaproveitados (`reuseExistingServer`) e rodam build velho: mate-os antes de medir.
