# Guardar lançamento por lançamento e reler só o que mudou

Type: task
Status: claimed
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

- [ ] Testes do armazenamento: gravar e ler por item, envio da fila regravando só os itens mudados, migração do bloco antigo guardado no aparelho
- [ ] Teste de que uma escrita em uma resposta não relê as outras
- [ ] Teste de que abrir a tela de lançamento faz um GET da lista só
- [ ] Testes de navegador sem internet seguem verdes
- [ ] Medir com `web/e2e/medir-historico.ts` antes e depois e registrar os números aqui
