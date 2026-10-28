# Esqueleto do repositório e do CI

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #81
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário nenhuma (fundação)

## O que construir

O repositório ganha o esqueleto do backend (FastAPI com uma rota de saúde), do app (React + TypeScript) e do CI, para que todo ticket seguinte nasça com testes rodando. É a primeira fatia: uma rota e uma tela mínimas, testadas de ponta a ponta.

## Checklist

- [x] Backend FastAPI com a rota de saúde, testada em processo contra um Postgres em container com migrations numeradas (um DDL por arquivo, no subconjunto do DSQL)
- [x] App React + TypeScript que chama a rota pelo cliente de tipos gerado do OpenAPI; o OpenAPI gerado fica versionado e o CI falha se ele ou os tipos estiverem desatualizados
- [x] Teste com navegador automatizado sobre o app servido localmente e a API local, com a rede desligável pelo teste
- [x] Valores iniciais da spec (3 sugeridos, 5 usos, 24 h, 80% etc.) num arquivo de configuração só
- [x] README curto com como rodar, testar e gerar os tipos
- [x] Verificações do projeto rodando e PR aberto para `main`
