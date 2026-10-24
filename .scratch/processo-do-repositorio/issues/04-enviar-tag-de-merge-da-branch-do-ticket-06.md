# Enviar a tag de merge da branch do ticket 06

Status: wontfix
Blocked by: —
Skills: nenhuma; HITL (o dono envia a tag de uma máquina com permissão)
Modelo recomendado: Sonnet
Effort recomendado: low
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add386343fd3e9df2e6d96a
Origem: fechamento do ticket [Em que mês conta uma compra no cartão](../../v1-substituir-mobills/issues/06-em-que-mes-conta-uma-compra-no-cartao.md); o envio de tags caiu de novo na sessão na nuvem ("the remote end hung up unexpectedly"), enquanto o push de branches funcionou

## Problema

O `AGENTS.md` pede a tag `merged/<branch>` em toda branch mesclada na `main`. A branch `claude/stoic-allen-813fm9` foi mesclada (o commit dela, `02b12bc`, entrou na `main` como `498b0a6` depois do rebase, junto com `b50543c`), mas `git push` da tag foi cortado três vezes. É a mesma falha de [Enviar a tag de merge da branch do mapa](02-enviar-tag-de-merge-da-branch-do-mapa.md).

## Checklist

- [ ] Dono cria e envia a tag no último commit da branch: `git fetch origin && git tag merged/claude/stoic-allen-813fm9 origin/claude/stoic-allen-813fm9 && git push origin merged/claude/stoic-allen-813fm9`
- [ ] Conferir que a tag aparece em `git ls-remote --tags origin`

## Resolução

Fechado sem enviar a tag. A regra de integração do `AGENTS.md` ("Integração por PR") não cria mais tag `merged/<branch>`: o PR mesclado com squash já registra a branch e o commit. Nenhuma pendência ficou em aberto.
