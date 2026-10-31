# Edição em lote interrompida no meio volta sozinha

Type: task
Status: ready-for-agent
Blocked by: 61
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #252
Origem: [ticket 61](61-edicao-em-lote.md): o lote grava em partes de uma transação cada (o limite de linhas do DSQL) e desfaz as anteriores quando uma parte é recusada, mas, se a Lambda cair ou estourar o tempo no meio, ninguém desfaz

## O que construir

Hoje a edição em lote que para no meio fica com a situação `aplicando`, com parte dos lançamentos mudada. Ela aparece em `#/edicoes-em-lote` com "A gravação parou no meio: desfaça para voltar o que já foi gravado", e reenviar o mesmo id só devolve o lote nesse estado. Isso quebra o "tudo ou nada" até alguém desfazer à mão.

## Checklist

- [ ] A tarefa diária (`app.tarefa_diaria.handler`) desfaz os lotes em `aplicando` há mais de alguns minutos (o tempo máximo da Lambda), como a compensação que `aplicar` já faz, e os marca `cancelada` com o motivo
- [ ] Decidir se o reenvio do mesmo id, com o lote parado há tempo, desfaz e aplica de novo, em vez de devolver o lote pela metade
- [ ] Teste de API que simula a parada no meio (partes gravadas, situação `aplicando`) e confere a volta
- [ ] README (seção Busca) e verificações do projeto rodando, PR aberto para `main`
