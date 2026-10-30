# Testes de navegador que ainda falham sob CPU saturada

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #233
Origem: [ticket 90](90-teste-do-recusado-intermitente.md): com 2 a 4 laços de CPU ocupando os 4 núcleos e `--repeat-each`, sobraram falhas que não aparecem na máquina livre (suíte inteira 106 de 106, banco limpo).

- `e2e/sem-internet.spec.ts` › "criado com a resposta perdida e depois editado ou excluído sem internet": o link "Editar" fica "not stable" (a lista reordena enquanto o `sync` reenvia a fila) ou "Salvar" fica desativado. Hipótese do 90 ainda de pé: o reenvio da fila disputa com o `setOffline(true)` do teste.
- `e2e/sem-internet.spec.ts` › "sem internet, as telas abertas...": "Salvar" desativado dentro de `lancar` (cadastro ainda não carregado na tela).

## Checklist

- [ ] Reproduzir com laços de CPU (`sh -c 'while :; do :; done'` x4) e `--repeat-each`
- [ ] Esperar no teste o sinal real (fila vazia, cadastro carregado) antes do próximo passo
- [ ] Suíte completa sem falha sob carga; PR aberto para `main`

## Notas

- Os testes do ticket 90 só são confiáveis com o banco limpo: o Postgres local acumula lançamentos entre rodadas (871 numa) e a suíte fica 3x mais lenta, com falhas de `toBeVisible` em `cadastrar`. Recrie o banco entre rodadas longas.
- Servidores do `webServer` que ficam de pé depois de uma rodada interrompida são reaproveitados (`reuseExistingServer`) e rodam build velho: mate-os antes de medir.
