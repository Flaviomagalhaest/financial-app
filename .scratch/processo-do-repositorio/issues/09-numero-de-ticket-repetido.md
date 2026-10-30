# Dois tickets com o número 95 na `main`

Type: task
Status: ready-for-human
Blocked by: —
Skills: decisão do dono (HITL); depois edição simples dos arquivos, das issues e dos links
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #225
Origem: sessão do ticket 95 (recorrência): o pedido "ticket 95" era ambíguo

## O problema

`.scratch/v1-substituir-mobills/issues/` tem dois arquivos `95-`: `95-acabamentos-da-aba-cartoes.md` (issue #189) e `95-recorrencia-reabrir-e-reagendar-sem-buraco.md` (issue #179). Os dois nasceram em sessões em paralelo no mesmo dia, e cada um tem links apontando para o seu número (ticket 45, ticket 55). O título da issue e do PR, `NN: título`, e o pedido "trabalhe no ticket 95" ficam ambíguos.

## Checklist

- [ ] O dono escolhe qual dos dois ganha novo número (o próximo livre no mapa) e se a regra de reserva do número precisa mudar (por exemplo, checar `origin` antes de criar um ticket)
- [ ] Renomear o arquivo, o título e o `Issue:`/título da issue, e os links dos tickets que o citam (o 45 cita o da recorrência; o 55 cita o dos cartões)
