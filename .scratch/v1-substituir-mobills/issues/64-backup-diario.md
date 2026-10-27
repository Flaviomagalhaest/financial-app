# Gerador de backup e backup diário

Type: task
Status: ready-for-agent
Blocked by: 28
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #118
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 157, 159, 160

## O que construir

Os dados passam a ter cópia diária que nem o root apaga. **Deve ser ligado antes de o casal lançar de verdade** ([ADR 0012](../../../docs/adr/0012-exportacao-unica-zip-de-csvs-e-restauracao-so-em-banco-vazio.md)).

## Checklist

- [ ] Gerador que só lê o banco e produz um zip com um CSV por tabela, ids originais e `manifesto.json` (`versao_formato`, contagens e somas)
- [ ] EventBridge diário grava o zip num S3 com versões e Object Lock em compliance por 90 dias, e confere as contagens do zip contra o banco
- [ ] Regra de ciclo de vida que apaga as versões depois dos 90 dias (o ticket 20 confere a ambiguidade na documentação)
- [ ] E-mail se o backup falhar ou não rodar em 26 horas
- [ ] Teste de API do gerador com o exemplo fictício
- [ ] Verificações do projeto rodando e PR aberto para `main`
