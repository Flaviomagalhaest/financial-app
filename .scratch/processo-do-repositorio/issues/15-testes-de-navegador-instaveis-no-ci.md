# Testes de navegador falham de forma diferente a cada execução do CI

Type: task
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: high
Issue: #422
Origem: o CI do PR #404 ([ticket 165](../../v1-substituir-mobills/issues/165-telas-que-filtram-a-lista-leem-do-servidor.md)). O [ticket 10](10-ci-vermelho-entra-na-main.md) foi `wontfix`; este é um defeito concreto, não a revisão do CI.

## O que se viu

Na suíte de navegador do `verificar` (274 testes, uma worker), cada execução do PR #404 falhou em testes diferentes, sem relação com o diff:

- execução 1: `lancamentos.spec.ts:5` (exclui um lançamento e o item não sai da lista) e `parcelamento.spec.ts:445` (antecipar sem internet: lê o servidor antes de a antecipação subir);
- nova execução do mesmo commit: `partes-na-recorrencia.spec.ts:187`;
- na máquina da sessão, `favoritos.spec.ts:106` falhou em duas execuções, uma delas num checkout limpo da `main` (`efa7240`), em 7 s;
- os mesmos testes passam sozinhos, repetidos.

Parte da causa do `parcelamento.spec.ts:445` era do PR (uma releitura que marcava a rede como sem resposta; corrigida no 165). As demais não têm causa achada.

## O que construir

Achar a causa de cada uma (esperas que dependem do tempo, estado dividido entre testes, a fila que sobe em segundo plano), com `retain-on-failure` de trace e vídeo no CI para a próxima falha deixar material. Não pular nem pôr `retries` para ficar verde.

## Checklist

- [x] `favoritos.spec.ts:106`: diagnosticado na `main` e consertado
- [x] `lancamentos.spec.ts:5`, `partes-na-recorrencia.spec.ts:187`: causa achada ou, sem causa, registrada aqui
- [x] `playwright.config.ts`: trace/vídeo guardados quando o teste falha, e o `ci.yml` os sobe como artefato
- [ ] Três execuções seguidas do `verificar` verdes na `main`: só depois do merge, movido para o [ticket 176](176-testes-de-navegador-tres-execucoes-verdes-na-main.md)

## Answer

O loop: a suíte inteira num banco novo, como o CI, e cada teste repetido (`--repeat-each`) contra os servidores de pé, com 3 ou 4 processos ocupando a CPU. Onde a repetição não bastou, sondas temporárias forçaram a janela: a leitura da fila no aparelho atrasada 500 ms num build de diagnóstico, ou uma leitura do servidor atrasada por `page.route`. Marcadores no envio do service worker e no `lerEGuardar` (pedidos a `/api/saude?...`, lidos no log da API) deram a ordem dos eventos. Tudo foi retirado antes do commit.

| Teste | Causa | Conserto | Antes → depois |
|---|---|---|---|
| `favoritos.spec.ts:106` | Os sugeridos são os 3 mais repetidos entre **todos** os lançamentos do casal. As 10 parcelas de um parcelamento de outro teste e o "Mercado" de outra rodada tiravam a Feira (6 usos) dos três primeiros: depende do que os testes anteriores deixaram no banco. | O teste dispensa antes os sugeridos que já existem (`api.criar` aceita a resposta 204). | 15 de 15 vermelhos no banco de uma suíte inteira → 5 de 5 verdes |
| `partes-na-recorrencia.spec.ts:187` | **Defeito do app.** A tela da recorrência preenche o formulário uma vez só, quando a regra chega. `useRecorrencias` punha a fila por cima da resposta guardada, mas, se a resposta chegava do IndexedDB antes da fila, a regra vinha sem a mudança não enviada e o formulário ficava com a regra de antes (a lista "⏳ partes, não enviado" aparecia, as partes não). | `useRecorrencias` só devolve a regra depois de ler a fila, como os favoritos (`filaLida`). Teste novo em `recorrencia-mudar.spec.ts` atrasa a leitura da fila e confere o formulário. | 1 de 15 com a CPU saturada; teste novo 3 de 3 vermelhos → 5 de 5 verdes |
| `sem-internet.spec.ts:521` (a falha mais comum do CI: 4 de 8 execuções) | **Defeito do teste.** A tela lê a lista várias vezes quando a rede volta (5 leituras na Hoje). O teste segurava só as de antes do lançamento do outro aparelho; a que saía logo depois e chegava ao servidor antes do POST guardava a lista sem ele, com o número mais novo. O service worker, achando a lista guardada (`temResposta`), não a lia, e o lançamento só chegava ao aparelho se uma leitura da tela batesse no servidor depois do POST. | As leituras da tela que saem depois também esperam o `soltar` e só então vão ao servidor. O service worker passa a ler e guardar, e as leituras mais velhas da tela são descartadas, que é o que o teste quer provar (ticket 122). | com a fila atrasada, 3 de 4 vermelhos → 4 de 4 verdes |
| `parcelamento.spec.ts:445` | Desde o 165, as parcelas da tela do parcelamento vêm do servidor e não ficam no aparelho. O teste desligava a rede logo depois de ver a descrição: se a leitura das parcelas não tinha respondido, a tela ficava sem parcelas por pagar e sem "Quitar tudo". | O teste espera as 6 parcelas antes de a rede cair. | 1 de 18 com a CPU saturada; com as parcelas atrasadas 1,5 s, 2 de 2 vermelhos → 2 de 2 verdes |
| `armazem.spec.ts:76` (novo, do 164) | `goto("/#/novo")` só muda o hash: a tela Novo abria ali e pedia a lista, e o reload logo abaixo cortava esse GET depois de o contador o ver. | `history.replaceState` troca o endereço sem abrir a tela. | 10 de 10 vermelhos → 20 de 20 verdes (10 com a CPU saturada) |
| `lancamentos.spec.ts:5` | Duas causas, as duas já com ticket: recarregar antes de a edição subir (corrigido no 164, que espera o envio) e a exclusão que vira conflito depois de uma edição cuja resposta se perdeu ([ticket 169](../../v1-substituir-mobills/issues/169-edicao-com-a-resposta-perdida-e-a-exclusao-seguinte.md)). | — | 25 repetições verdes aqui, sozinho e com a CPU saturada |
| `fatura-paga.spec.ts:119` | A única falha (execução 41697749709) foi no PR do 164, antes da correção que ele mesmo fez (a correção abria antes de a fatura listar a compra). | — | 15 repetições com a CPU saturada e sete leituras atrasadas uma a uma, todas verdes |

O modo antigo do `parcelamento.spec.ts:445` (a antecipação não aplicada, nos CIs de 02/11) não se reproduziu e foi para o [ticket 176](176-testes-de-navegador-tres-execucoes-verdes-na-main.md), com as três execuções da `main`.

Suíte inteira num banco novo, com tudo isto: 279 de 279 verdes (19 min). Sem seam: nenhum. O conserto do app tem teste próprio (`recorrencia-mudar.spec.ts`, "a tela da recorrência espera a fila"); os outros são consertos dos próprios testes.

Observação: a Hoje lê a lista 5 vezes quando a rede volta (marcadores do `lerEGuardar`), porque a leitura que não respondeu não junta as seguintes (`juntarDesde` vale só na mesma tarefa do navegador). Não é falha de teste nem foi medido como problema; fica registrado aqui caso alguém volte ao "um GET por tela" do 164.
