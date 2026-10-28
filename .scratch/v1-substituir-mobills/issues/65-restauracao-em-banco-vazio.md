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

## Comments

- 2026-10-28 (do [ticket 64](64-backup-diario.md)): o gerador está em `backend/app/backup.py` (`gerar_backup`, `conferir_backup`, `VERSAO_FORMATO = 1`). Ele descobre as tabelas do schema `public` sozinho (fora `controle_de_migrations`), escreve cada valor como `::text` do Postgres, `NULL` como campo vazio sem aspas e todo o resto entre aspas (`csv.QUOTE_NOTNULL`), em ordem de chave primária, e o manifesto traz por tabela `linhas` e `somas` das colunas inteiras e `numeric`. Pontos para a restauração:
  - o `::text` de `timestamptz` depende do `TimeZone` da sessão: fixe o mesmo fuso na geração e na restauração, ou a ida e volta não dá zip idêntico entre sessões com fusos diferentes;
  - as consultas ao `pg_catalog` (`pg_constraint` com `unnest ... WITH ORDINALITY`) e ao `information_schema` só rodaram no DSQL com o banco sem tabelas do domínio; a restauração de verdade no `dev` deste checklist é a primeira a exercitá-las com tabelas;
  - falta uma guarda que obrigue subir `versao_formato` quando uma migration muda as tabelas (o ADR 0012 pede); o gerador aceita qualquer esquema.
