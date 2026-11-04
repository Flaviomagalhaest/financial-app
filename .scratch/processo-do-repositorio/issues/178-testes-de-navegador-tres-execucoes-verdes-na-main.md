# Testes de navegador: três execuções verdes na main e as próximas falhas com trace

Type: task
Status: claimed
Blocked by: 15
Skills: `diagnosing-bugs`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #440
Origem: o que o [ticket 15](15-testes-de-navegador-instaveis-no-ci.md) não pôde fechar na branch: a verificação na `main` só vem depois do merge, e um modo de falha antigo ficou sem causa.

## O que fazer

Depois do merge do 15, rodar o `verificar` da `main` três vezes seguidas (workflow `CI`, "Re-run all jobs" no último push da `main`, sem mudar nada). Cada falha deixa trace e vídeo no artefato `testes-com-navegador` da execução: baixar, abrir com `npx playwright show-trace`, achar a causa e consertar (sem `retries` nem pular o teste).

Modo de falha ainda sem causa: `parcelamento.spec.ts:445` nos CIs da `main` de 02/11 (execuções 41467481476 e 41469168507) terminava com a antecipação não aplicada (as 5 parcelas seguintes ainda previstas, de R$ 100,00) e a fila vazia. O 15 não o reproduziu: 25 repetições sozinho e com a CPU saturada, leitura da fila atrasada, e a corrida que achou (a rede cair antes de as parcelas chegarem) falha em outro ponto. Parte da causa daquela época era a releitura que marcava a rede como sem resposta, corrigida no 165.

## Checklist

- [ ] Três execuções seguidas do `verificar` verdes na `main`
- [ ] Cada falha que aparecer: causa achada pelo trace do artefato e consertada, ou registrada aqui com o trace
- [ ] `parcelamento.spec.ts:445` com a antecipação não aplicada: causa achada, ou nenhuma ocorrência nas execuções acima
