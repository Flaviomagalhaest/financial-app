# Sugeridos conta as parcelas de uma compra parcelada como usos

Type: bug
Status: resolved
Blocked by: —
Skills: `triage`, `diagnosing-bugs`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #534
Origem: [ticket 204](204-acabamento-visual-do-app.md). Nas capturas da base de teste (08/11), uma única compra de geladeira em 10 parcelas aparece em Hoje › Sugeridos como "Geladeira, 10 usos", com a oferta de favoritar.

## Problema

Uma compra parcelada é um lançamento só do ponto de vista de quem lança, mas a contagem de usos (`backend/app/sugestao.py` ou `backend/app/favoritos.py`; o texto sai em `web/src/lancamentos/SugeridosDeFavorito.tsx:33`) parece contar cada parcela. O resultado é sugerir favoritar algo que a pessoa lançou uma vez.

O mesmo pode valer para lançamentos gerados por recorrência; confirmar na triagem se a recorrência deve ou não contar.

## Checklist

- [x] Reproduzir num teste: uma compra em 10 parcelas não gera sugestão
- [x] Decidir se recorrências contam como usos: precisa do dono, registrado no [ticket 212](212-recorrencias-contam-como-usos-do-sugerido.md); a contagem de recorrência não mudou
- [x] Corrigir a contagem (`_grupos` conta um uso por parcelamento); specs e verificações verdes; PR para `main`
