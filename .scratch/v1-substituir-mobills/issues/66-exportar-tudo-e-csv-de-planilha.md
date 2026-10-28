# "Exportar tudo" no app e CSV de planilha

Type: task
Status: resolved
Blocked by: 64, 31
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #120
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 157, 158, 163

## O que construir

O casal baixa os dados a qualquer momento.

## Checklist

- [x] `POST /api/exportacoes` gera o backup ou o CSV e devolve URL assinada de 5 minutos; cada exportação a pedido fica registrada (quem e quando)
- [x] Formato do CSV de lançamentos para planilha: separador `;`, vírgula decimal, UTF-8 com BOM, sem filtro por período
- [x] Nomes no lugar dos ids: a consulta aos lançamentos foi movida para o [ticket 77](77-ligar-o-csv-de-planilha-ao-esquema-real.md), porque as tabelas ainda não existem (hoje a planilha sai só com o cabeçalho)
- [x] Botão nas configurações, só com internet
- [x] Habilita o [ticket 26](26-verificar-o-download-da-exportacao-no-iphone.md) (verificar o download no iPhone)
- [x] Verificações do projeto rodando e PR aberto para `main`

## Comments

- 2026-10-28 (do [ticket 64](64-backup-diario.md)): use `gerar_backup` de `backend/app/backup.py` numa transação `REPEATABLE READ` só de leitura, como `fazer_backup_diario` em `backend/app/backup_diario.py`, para tabelas, contagens e somas saírem do mesmo instante. As exportações a pedido precisam de outro bucket: o bucket do backup tem retenção padrão de Object Lock em compliance para o bucket inteiro (90 dias em `prod`), e o ADR 0012 manda separar as exportações, com expiração de 7 dias.

## Answer

Entregue em `ticket-66`:

- `POST /api/exportacoes` (`backend/app/exportacao.py`) recebe `{"formato": "backup" | "planilha"}`, lê o banco numa transação `REPEATABLE READ` só de leitura (o backup passa por `gerar_backup` e `conferir_backup`, como o diário), grava em `exportacoes/<uuid>.zip|csv` no bucket de `EXPORTACOES_BUCKET` e devolve `{url, arquivo, expira_em}` com a URL assinada de 300 segundos (tipo e nome do arquivo vêm da assinatura). O registro (quem, formato, quando) vai para a tabela `exportacoes` (migration 0002) só depois de o arquivo existir, então um pedido que falhou não conta; a tabela entra no backup.
- Bucket próprio `Exportacoes` na pilha de dados (sem Object Lock, expiração de 7 dias no prefixo `exportacoes/`), separado do bucket do backup. A role da API ganha só `PutObject` e `GetObject` nesse prefixo; o timeout da Lambda da API foi para 29 s (limite da HTTP API é 30 s).
- App: tela Configurações (link no topo) com os dois botões; sem internet ficam desligados com o aviso "Exportar precisa de internet."; a URL assinada é aberta com `window.location.assign`, e o S3 responde como download.
- O [ticket 26](26-verificar-o-download-da-exportacao-no-iphone.md) está liberado.

Pendências gravadas: [ticket 77](77-ligar-o-csv-de-planilha-ao-esquema-real.md) (consulta do CSV de planilha, bloqueado pelas tabelas de lançamentos, contas, cartões, categorias e tags). O download por `window.location.assign` e o bucket novo só foram exercitados com S3 falso e URL simulada; o teste de verdade (AWS e iPhone) é o ticket 26 e a conferência do `dev` no deploy.
