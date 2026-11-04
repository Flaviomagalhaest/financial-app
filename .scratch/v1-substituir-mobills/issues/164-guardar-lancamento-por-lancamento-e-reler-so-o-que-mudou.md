# Guardar lançamento por lançamento e reler só o que mudou

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`, `codebase-design`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: high
Issue: #396
Origem: [ticket 124](124-historico-sem-a-lista-inteira.md) e [ADR 0024](../../../docs/adr/0024-sem-internet-so-a-janela-do-aparelho.md) (decisão Q2). Achados do [ticket 123](123-historico-com-o-volume-real.md).

## O que construir

Três correções no armazenamento do aparelho (`web/src/dados/armazem.ts`, `index.ts`, `fila.ts`), que valem para qualquer tamanho de lista e preparam a [janela do aparelho](166-janela-do-aparelho.md):

- **Lançamento por lançamento**: hoje a lista inteira é um bloco só em `respostas` sob `/api/lancamentos`, regravado inteiro a cada envio da fila (`aplicar`, `fila.ts`). Guardar cada lançamento como um registro, para o envio gravar só os que mudaram.
- **Avisar só quem lê a resposta que mudou**: `ouvirMudancas` avisa todos os ouvintes a cada escrita, e cada hook relê a resposta dele inteira (54 leituras da lista numa abertura do Histórico). O ticket 123 baixou para 6 e desfez a mudança, que vale fazer agora.
- **Um GET da lista por tela**: cada hook que lê `LISTA` dispara o próprio GET (a tela de lançamento dispara 5 ao abrir). Juntar os pedidos iguais em andamento.

## Checklist

- [x] Testes do armazenamento: gravar e ler por item, envio da fila regravando só os itens mudados, migração do bloco antigo guardado no aparelho
- [x] Teste de que uma escrita em uma resposta não relê as outras
- [x] Teste de que abrir a tela de lançamento faz um GET da lista só
- [x] Testes de navegador sem internet seguem verdes
- [x] Medir com `web/e2e/medir-historico.ts` antes e depois e registrar os números aqui

## Resultado

- **Por item** (`armazem.ts`): o banco do aparelho foi para a versão 2, com a loja `lancamentos` (um registro por lançamento, pelo `id`). Em `respostas`, sob `/api/lancamentos`, fica só a hora e o número da leitura. A migração está no `onupgradeneeded`: o bloco da versão 1 vira registros. `lerResposta(LISTA)` monta a lista da loja. A leitura do servidor grava só os lançamentos que mudaram e apaga os que não vieram mais. O envio da fila (`aplicar`, `fila.ts`) grava e apaga só os lançamentos enviados. `temResposta` diz se a lista está guardada sem lê-la inteira (o envio da tela e o do service worker).
- **Aviso por chave**: `ouvirMudancas(chaves, ouvinte)`. A transação anota o que gravou (o caminho da resposta, `NA_FILA`, ou a lista quando mexe em `lancamentos`) e avisa só quem ouve essas chaves, aqui e pelo `BroadcastChannel`. O aviso de uma versão anterior, que não diz o quê, vale como tudo.
- **Um GET por tela**: as leituras automáticas dos hooks (ao abrir, a rede voltar, o app voltar à frente) juntam-se à do mesmo caminho pedida na mesma tarefa do navegador, e não a qualquer uma em andamento. A primeira versão juntava a qualquer uma e quebrou `estorno.spec.ts`: a tela da fatura, aberta depois de a API criar o estorno, ficou com a leitura que o Histórico tinha pedido antes. A leitura que a tela pede depois de mudar o servidor (`buscar`, `relerAsParcelas`...) sai sempre sozinha.
- **Testes**: `web/e2e/armazem.spec.ts` (um GET na tela de lançamento: eram 5; as categorias chegam e a lista não é relida; o envio grava 1 lançamento, eram 10 numa lista de 10; a lista em bloco da versão anterior aparece sem internet). `sem-internet.spec.ts` (15) verde; suíte inteira 270 de 273 num banco local com dados de várias rodadas, e as 3 que falharam (`estorno-de-parte-e-parcelas`, `fatura-paga`, `favoritos`) passam num banco novo, como no CI.
- **Medida** (`web/e2e/medir-historico.ts`, que agora conta as gravações e leituras por item; 3.000 lançamentos do gerador do ticket 112, CPU 4x mais lenta, 3 rodadas, recarregar o Histórico com um lançamento novo vindo da API):

| | antes | depois |
|---|---|---|
| até mostrar (mediana) | 13,8 s (9,0 a 15,0) | 7,2 s (6,9 a 8,1) |
| leituras da lista guardada por abertura | 61 | 6 |
| lançamentos gravados na releitura | 3.001 (a lista inteira) | 1 (o novo) |
| GET da lista por abertura do Histórico | 1 | 1 |

  O que sobra é o render da lista inteira (JS, layout e estilo somam uns 5 s dos 7), que é o [ticket 167](167-historico-desenhado-mes-a-mes.md). O prazo de 15 s de `lerAListaInteira` (`sem-internet.spec.ts`) fica para ele, como o 167 já diz.
- **CI**: a primeira escrita da lista num aparelho vazio (o caso de todo teste, cada um num contexto novo do navegador) grava um registro por lançamento e leva mais que o bloco de antes (uns 140 ms com 1.700 lançamentos, contra uns 150 ms do GET até a tela na `main`). Isso expôs duas corridas de teste que a `main` também tem com mais dados no banco. `fatura-paga.spec.ts` abria a correção antes de a fatura listar a compra, e agora espera a compra aparecer. `lancamentos.spec.ts` recarregava antes de a edição subir, e agora espera o envio.
- **Pendências**:
  - a aba que estava aberta com a versão anterior do app passa a receber `VersionError` do IndexedDB depois da migração, até ser recarregada: [ticket 168](168-aba-aberta-numa-versao-anterior-do-app.md) (`ready-for-human`);
  - a edição cuja resposta se perdeu não sobe ao reabrir o app, e a exclusão seguinte volta como conflito com ela, também na `main`: [ticket 169](169-edicao-com-a-resposta-perdida-e-a-exclusao-seguinte.md).
