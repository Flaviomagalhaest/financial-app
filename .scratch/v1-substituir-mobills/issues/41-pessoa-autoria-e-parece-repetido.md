# Pessoa, autoria e "Parece repetido"

Type: task
Status: resolved
Blocked by: 34
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #95
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 20, 61, 62

## O que construir

Cada lançamento diz de quem é (ou que é do casal), quem o criou e quem o alterou por último, e o app avisa quando o casal lançou a mesma coisa duas vezes.

## Checklist

- [x] Campo pessoa (Flávio, esposa ou conjunto) no lançamento e no formulário
- [x] Menu ⋯ > Informações com quem criou, quem alterou por último e quando (hora da ação no aparelho); origem "app" ou "importado do Mobills"
- [x] "Parece repetido" quando chega lançamento da outra pessoa com mesmo valor, mesma conta ou cartão e data a até 1 dia, com "Manter os dois" ou "Excluir este" (só a conta: o cartão não existe ainda, linha no ticket 37)
- [x] A tela de conflito e o aviso de exclusão (ticket 34, `TelaDeConflito.tsx` e `ListaDeLancamentos.tsx`) dizem o nome ("o da Fulana, às 14:32", "Fulana excluiu este lançamento") no lugar de "a outra pessoa", e a hora é a da ação no aparelho, não a da chegada ao servidor (`alterado_em` de `lancamento_campos` é o `now()` do servidor)
- [x] Testes de API e de navegador com dois contextos
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas da implementação

- **Pessoa**: o lançamento tem `pessoa` (o id de uma das pessoas do casal; vazio é o conjunto), campo versionado como os outros (`CAMPOS` em `lancamentos.py` e `fila.ts`): mudar a pessoa que o outro lado mudou depois é conflito. Na edição, `pessoa` ausente fica como está e `""` volta para o conjunto. As pessoas vêm de `PESSOAS` (`app/pessoas.py`, JSON `{"<sub>": "<nome>"}`), lido em `GET /api/pessoas` com `eu` marcando quem chama; o app guarda a lista como as outras leituras, e sem a variável a API aceita qualquer pessoa e o app diz "a outra pessoa" (ticket [84](84-ligar-as-pessoas-do-casal-ao-ambiente.md)). O seletor "Pessoa" fica na folha Detalhes.
- **Hora da ação**: criar, editar, confirmar e excluir (e as ações do lote) levam `acao_em`, a hora em que a pessoa agiu no aparelho (`feitoEm` do item da fila, a última ação sobre ele); o servidor grava essa hora em `criado_em`, `alterado_em`, na versão de cada campo (`lancamento_campos.alterado_em`) e em `excluido_em`, nunca depois do relógio dele (`_momento`). Sem `acao_em` (app antigo), vale a da chegada. Consequência: `criado_em` é hora de aparelho, e a ordem entre lançamentos de aparelhos diferentes pode não bater com a de chegada.
- **Autoria e origem**: o menu ⋯ > Informações de cada linha do Histórico mostra quem criou, quem alterou por último (nome, "você" para o próprio aparelho) e quando, e a origem "app" ou "importado do Mobills" (`fonte`, que só o importador, ticket 67, grava; vazia é "app"). O que só existe no aparelho diz "ainda não enviado".
- **Parece repetido**: o servidor marca `parece_repetido_de` no lançamento que chegou depois (menor `criado_em`, desempate pelo id, é o original) quando outra pessoa tem um com mesmo valor, tipo e conta e data a até `pareceRepetidoDias` (1, `config/valores-iniciais.json`) e o casal ainda não conferiu. Só vê o aviso quem **não** criou o que chegou depois, com "Manter os dois" (`POST /api/lancamentos/{id}/manter-os-dois`, grava `repetido_mantido_em`, não sobe a versão e **precisa de internet**) e "Excluir este" (a exclusão comum, pela fila). Excluir um dos dois tira o aviso do outro. Só conta lançamentos (transferência fica de fora) e o importado do Mobills fica de fora dos dois lados. "Chegou depois" é pelo `criado_em`, que é hora de aparelho: um lançamento criado offline e enviado tarde pode ser o "original".
- **Nomes**: a tela de conflito diz "O de <nome>, às 14:32" e o aviso de exclusão, "<nome> excluiu este lançamento"; a hora é a da ação no aparelho. A tela de decisão ganhou o campo Pessoa.
- **Backup**: formato 9, com conversor da 8 (`pessoa`, `fonte` e `repetido_mantido_em` vazios nos antigos). Migrations 0019 a 0021.
- **Não coberto por teste de navegador**: a hora da ação no aparelho (a diferença entre o relógio do aparelho e o do servidor é pequena demais para o teste do navegador); fica coberta pelos testes de API (`test_pessoa_e_autoria.py`).
- **Reserva**: commitada na própria branch de trabalho, como nos tickets 33 e 34.
- **Pendências**: [84](84-ligar-as-pessoas-do-casal-ao-ambiente.md) (`PESSOAS` com os `sub` reais nos ambientes, do dono) e [85](85-nomes-nos-avisos-da-outra-pessoa.md) (dois avisos que seguem genéricos); linhas novas nos tickets [37](37-cartoes-e-faturas.md) (o "Parece repetido" também compara cartão), [67](67-importador-do-mobills-cruzamento-e-revisao.md) (gravar `fonte = 'mobills'`) e [77](77-ligar-o-csv-de-planilha-ao-esquema-real.md) (coluna pessoa pelo nome).
