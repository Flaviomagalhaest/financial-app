# Restauração em banco vazio

Type: task
Status: ready-for-agent
Blocked by: 64
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #119
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 161, 162

## O que construir

O dono refaz o banco a partir de um backup com confiança.

## Checklist

- [ ] Restaura tudo ou nada, só em banco vazio, e confere contagens e somas contra o manifesto; recusa banco com dados e versão de formato desconhecida
- [ ] Conversores das versões antigas do formato
- [ ] Teste de ida e volta no CI: restaurar o backup fictício, exportar de novo e exigir zip idêntico; restaurar versão antiga
- [ ] Restauração de verdade no `dev` a partir do backup de `prod`, antes da virada e a cada mudança no formato
- [ ] Verificações do projeto rodando e PR aberto para `main`
