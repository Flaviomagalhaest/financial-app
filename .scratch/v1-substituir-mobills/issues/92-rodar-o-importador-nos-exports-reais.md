# Rodar o importador do Mobills nos exports reais e conferir

Type: task
Status: ready-for-human
Blocked by: —
Skills: `run` (o dono roda localmente; HITL: só ele tem os exports reais)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #174
Origem: [ticket 67](67-importador-do-mobills-cruzamento-e-revisao.md) (o importador só rodou sobre exports fictícios; dado real nunca entra no repositório nem no CI)

## O que fazer

O dono roda o importador sobre `data/historic/` (fora do git) e cola aqui **só contagens**, sem nenhum dado real:

```sh
(cd backend && uv run python -m app.mobills <pasta do geral> <pasta das faturas> <planilha.xlsx>)
```

## Checklist

- [ ] Layout: o geral numa pasta, uma subpasta por cartão com os arquivos `<cartão>_-_<AAAAMM>.xlsx`; se os exports estiverem em outro arranjo, ajustar `backend/app/mobills/leitura.py`
- [ ] Taxa de casamento perto dos 97,7% do [ticket 18](18-importacao-do-mobills-cartao-e-datas.md) (4.618 exatos, 11 só sem a categoria, 2 prováveis, 111 sem par); se ficar longe, diagnosticar a comparação da descrição (hoje sem diferença de maiúsculas e de espaços)
- [ ] Separador de várias tags: conferir no export real se é a vírgula (`_tags` em `leitura.py` é uma aposta; os exports de teste só tinham uma tag por linha)
- [ ] A Conferência termina no último mês com lançamento pago: confirmar que é o mês do export (a virada) e que os meses seguintes, só de previstos, podem ficar de fora
- [ ] Dono preenche a coluna Mobills da Conferência e das Faturas em alguns meses, roda de novo e confere a diferença e o "Por quê"
- [ ] Dono diz se as abas Grupos ambíguos e Parcelas quebradas bastam como informação ou se precisam de uma coluna de decisão (hoje só informam: o ticket 18 manda o grupo e a sequência "para a revisão" sem dizer o que o dono decide); se precisar, vira ticket
- [ ] Contagens e respostas gravadas em `## Answer`
