# Enviar a tag de merge da branch do mapa

Status: done
Blocked by: —
Skills: nenhuma; HITL (o dono envia a tag de uma máquina com permissão)
Modelo recomendado: Sonnet
Effort recomendado: low
Origem: traçado do mapa [V1 que substitui o Mobills](../../v1-substituir-mobills/map.md); a sessão na nuvem enviou as branches, mas o envio de tags caiu com desconexão

## Problema

O `AGENTS.md` pede a tag `merged/<branch>` em toda branch mesclada na `main`. A branch `claude/great-bohr-z1cqpa` foi mesclada, mas `git push` de `refs/tags/...` é cortado nesta sessão, enquanto o push de branches funciona.

## Checklist

- [x] Dono cria e envia a tag no último commit da branch: `git fetch origin && git tag merged/claude/great-bohr-z1cqpa origin/claude/great-bohr-z1cqpa && git push origin merged/claude/great-bohr-z1cqpa`
- [x] Conferir que a tag aparece em `git ls-remote --tags origin`
