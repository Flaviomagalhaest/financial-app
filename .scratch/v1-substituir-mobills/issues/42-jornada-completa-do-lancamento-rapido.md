# Jornada completa do lançamento rápido

Type: task
Status: ready-for-agent
Blocked by: 36, 40, 41
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #96
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 10-19, 22, 23, 24

## O que construir

A tela de lançar chega ao desenho dos protótipos: lançar uma despesa leva poucos segundos. A fonte de verdade da interface é a variante A da branch `prototipo/lancamento-rapido`.

## Checklist

- [ ] Fileiras de toque para conta ou cartão e categorias; folha de detalhes com descrição, tags, pessoa, data, parcelado e recorrente (os dois últimos ficam desativados até seus tickets), e resumo numa linha
- [ ] Data entre hoje, ontem ou outra; data futura nasce prevista e passada ou de hoje nasce realizada, trocável à mão
- [ ] "Repetir último" enquanto o lançamento está vazio
- [ ] Atalho "Novo lançamento" funcionando no Android e botão na tela inicial no iPhone
- [ ] Teste de navegador do fluxo completo, online e offline
- [ ] Verificações do projeto rodando e PR aberto para `main`
- [ ] Da revisão do ticket 32: data com "hoje / ontem / outra" (história 18) e a linha de resumo dos detalhes embaixo do valor (história 17); hoje a data é só um campo em "Detalhes"
