# Testes de navegador falham de forma diferente a cada execução do CI

Type: task
Status: claimed
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

- [ ] `favoritos.spec.ts:106`: diagnosticado na `main` e consertado
- [ ] `lancamentos.spec.ts:5`, `partes-na-recorrencia.spec.ts:187`: causa achada ou, sem causa, registrada aqui
- [ ] `playwright.config.ts`: trace/vídeo guardados quando o teste falha, e o `ci.yml` os sobe como artefato
- [ ] Três execuções seguidas do `verificar` verdes na `main`
