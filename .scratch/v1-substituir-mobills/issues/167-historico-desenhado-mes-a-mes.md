# Histórico desenhado mês a mês e continuado pelo servidor

Type: task
Status: ready-for-agent
Blocked by: 166
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #399
Origem: [ticket 124](124-historico-sem-a-lista-inteira.md) e [ADR 0025](../../../docs/adr/0025-sem-internet-so-a-janela-do-aparelho.md) (decisão Q5).

## O que construir

O Histórico (`ListaDeLancamentos.tsx`) desenha hoje um `<ul>` com todos os lançamentos. Passa a desenhar mês a mês, com cabeçalho de mês: mostra os meses mais recentes e desenha o mês anterior quando a pessoa chega ao fim da tela. Depois do fim da janela do aparelho, com internet, continua lendo do servidor mês a mês, sem guardar no aparelho. Sem internet, o fim da janela mostra "Para ver antes de <mês>, conecte-se à internet".

## Checklist

- [ ] Testes de navegador: cabeçalho de mês, o mês anterior ao rolar, a continuação pelo servidor depois da janela e o aviso de fim sem internet
- [ ] Voltar ao padrão o prazo do teste "a rede volta, mas a lista não chega antes do envio" (`web/e2e/sem-internet.spec.ts`, `lerAListaInteira`)
- [ ] Medir com `web/e2e/medir-historico.ts` (1.600, 6 mil e 11 mil lançamentos, CPU 4x) e registrar aqui o tempo até mostrar
