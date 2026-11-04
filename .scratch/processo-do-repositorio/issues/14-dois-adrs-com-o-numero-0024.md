# Dois ADRs com o número 0024

Type: task
Status: claimed
Blocked by: —
Skills: `domain-modeling`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #421
Origem: revisão do [ticket 165](../../v1-substituir-mobills/issues/165-telas-que-filtram-a-lista-leem-do-servidor.md) (PR #404): `docs/adr/` tem dois arquivos 0024, criados no mesmo dia (03/11) por sessões em paralelo.

## O que construir

- `docs/adr/0024-a-geracao-so-lanca-de-hoje-em-diante.md` (commit `f1076b2`)
- `docs/adr/0024-sem-internet-so-a-janela-do-aparelho.md` (commit `4d1dc3b`)

"ADR 0024" fica ambíguo em tickets, comentários de código e na [ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md). Renumerar um dos dois para 0025 (o que entrou depois) e acertar todas as referências, sem mudar o texto das decisões. Atenção: os comentários do código dos tickets 165 e 166 dizem "ADR 0024" querendo dizer a da janela do aparelho.

## Checklist

- [ ] Renomear o arquivo e o título do ADR que entrou depois
- [ ] Trocar as referências a ele em `docs/`, `.scratch/`, `GLOSSARY.md`, `backend/` e `web/` (busca por `0024` e pelo nome do arquivo)
- [ ] Conferir que nenhum link ficou quebrado
