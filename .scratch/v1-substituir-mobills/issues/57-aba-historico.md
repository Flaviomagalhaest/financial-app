# Aba Histórico

Type: task
Status: resolved
Blocked by: 54
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #111
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 134

## O que construir

O casal vê a evolução de longo prazo desde 2019.

## Checklist

- [x] Uma métrica por vez (despesas, receitas, sobra ou uma categoria) em 12 meses contra os 12 anteriores, por ano ou o mesmo mês em cada ano
- [x] Respeita a regra de o dashboard responder em menos de 1 s; se passar, registrar ticket para agregado mensal (não passou: 30 a 60 ms com 11 mil lançamentos)
- [x] Testes de API
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas da implementação

- **Uma leitura por tela**: `GET /api/historico` (`backend/app/historico.py`, testes em `backend/tests/test_aba_historico.py`) serve as três visões da métrica escolhida; a tela (`web/src/historico/TelaDaEvolucao.tsx`) fica no topo da aba Histórico, acima da lista de lançamentos, e o app guarda a resposta de cada combinação para mostrar sem internet. Teste de navegador em `web/e2e/historico.spec.ts`.
- **Desempenho**: 11 mil lançamentos de 2019 a hoje no Postgres local deram 30 a 60 ms por leitura; sem ticket de agregado mensal.
- **Pendências**: as regras provisórias vão para o dono no [ticket 109](109-regras-provisorias-da-aba-historico.md).
