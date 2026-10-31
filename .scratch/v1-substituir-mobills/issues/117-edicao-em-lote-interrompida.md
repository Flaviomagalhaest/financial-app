# Edição em lote interrompida no meio volta sozinha

Type: task
Status: resolved
Blocked by: 61
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #252
Origem: [ticket 61](61-edicao-em-lote.md): o lote grava em partes de uma transação cada (o limite de linhas do DSQL) e desfaz as anteriores quando uma parte é recusada, mas, se a Lambda cair ou estourar o tempo no meio, ninguém desfaz

## O que construir

Hoje a edição em lote que para no meio fica com a situação `aplicando`, com parte dos lançamentos mudada. Ela aparece em `#/edicoes-em-lote` com "A gravação parou no meio: desfaça para voltar o que já foi gravado", e reenviar o mesmo id só devolve o lote nesse estado. Isso quebra o "tudo ou nada" até alguém desfazer à mão.

## Checklist

- [x] A tarefa diária (`app.tarefa_diaria.handler`) desfaz os lotes em `aplicando` há mais de alguns minutos (o tempo máximo da Lambda), como a compensação que `aplicar` já faz, e os marca `cancelada` com o motivo
- [x] Decidir se o reenvio do mesmo id, com o lote parado há tempo, desfaz e aplica de novo, em vez de devolver o lote pela metade
- [x] A compensação de uma parte recusada usa o desfazer, que pula o lançamento mudado depois: se alguém mexer num lançamento já gravado enquanto o lote ainda grava, ele fica com a mudança do lote e o lote vira `cancelada` sem avisar ninguém. Decidir se a compensação volta só as categorias e tags que o lote pôs (sem tocar no que a outra pessoa mudou), ou se avisa quais ficaram (revisão do ticket 61)
- [x] Teste de API que simula a parada no meio (partes gravadas, situação `aplicando`) e confere a volta
- [x] README (seção Busca) e verificações do projeto rodando, PR aberto para `main`

## Decisões

- Parado = em `aplicando` há mais de 5 minutos (`PARADO_HA`): a Lambda da API tem 29 s, então a folga é grande.
- Reenvio do mesmo id, com o lote parado há tempo: desfaz, marca `cancelada` e responde 422 com o motivo; não grava de novo com o mesmo id (o aparelho manda um lote novo). Dentro dos 5 minutos continua devolvendo o lote como está.
- Compensação: mantém o desfazer (pula o que mudou depois) e **avisa**: o motivo do lote `cancelada` diz quantos lançamentos ficaram com a mudança do lote. Não há tela que mostre o lote cancelado; o aviso aparece só na resposta do reenvio e no banco.
