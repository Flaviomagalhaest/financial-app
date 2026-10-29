# Sugestão pelo histórico

Type: task
Status: resolved
Blocked by: 42
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #117
Origem: [spec da v1](../spec.md), etapa 6; histórias de usuário 38, 39, 40, 41, 42, 43

## O que construir

Ao digitar a descrição, o app oferece categorias, tags, conta e pessoa de um lançamento parecido, sem internet ([ticket 22](22-sugestao-automatica-de-categorias-e-tags.md)).

## Checklist

- [x] Contrato de fonte de sugestão (entrada: descrição e contexto; saída: pacotes com origem); a v1 entrega só a fonte "histórico", que no servidor produz o índice levado ao aparelho no pacote para lançar
- [x] Casamento no aparelho: igual, começa com, palavra que começa com; sem acento e maiúscula e sem `(n/total)`; a partir de 2 letras, até 3 pacotes, do mais recente ao mais antigo
- [x] Escolher preenche os campos e mantém o valor; corrigir as categorias torna essa a sugestão mais recente
- [x] Testes de API do índice e de navegador sem internet
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas da implementação

- **Fonte de sugestão**: o contrato é o `FonteDeSugestao` de `web/src/dados/sugestao.ts` (entra a descrição e o `ContextoDaSugestao`; sai uma lista de `Sugestao`, cada uma com `origem`). A v1 só tem a `fonteDoHistorico`, que ignora o contexto. No servidor, `backend/app/sugestao.py` monta o índice.
- **Índice**: `GET /api/sugestoes` devolve `gerado_em` e as sugestões (descrição, `chave` normalizada, tipo, conta, categorias, tags, pessoa, `em` e `origem: "historico"`), com até 3 diferentes por descrição, da mais recente à mais antiga. Uma mais antiga que essas nunca entra na lista de ninguém, então o índice fica pequeno. A recência é a criação ou a última mudança na descrição, no tipo, na conta, nas categorias, nas tags ou na pessoa (`lancamento_campos`). O previsto de recorrência conta pela hora da regra, para a ocorrência que a tarefa diária cria depois não passar na frente de uma correção. Ficam de fora o excluído, a descrição vazia e a categoria e a tag arquivadas. Transferências e ajustes de fatura não são lançamentos, e o importado do Mobills entra como qualquer lançamento.
- **Sem "pacote para lançar" único**: a spec fala do índice "no pacote para lançar", mas o ticket 33 fez o pacote como leituras guardadas uma a uma na camada de dados. O índice é mais uma delas, buscada também logo depois de cada envio da fila (ao abrir, ao voltar ao app e quando a rede volta), e não só ao abrir o novo lançamento.
- **No aparelho**: o `useSugestao` põe por cima do índice os lançamentos que ele ainda não tem, os não enviados e os que mudaram depois de `gerado_em`. Lançar ou corrigir sem internet já muda a ordem. As imprecisões até o índice ser buscado de novo ficaram no [ticket 101](101-sugestao-no-aparelho-ate-o-indice-ser-buscado-de-novo.md).
- **Na tela**: a lista aparece abaixo da descrição, na folha de detalhes, quando se digita, e some ao escolher. Cada linha traz a descrição e o resumo ("Mercado · #feira · Nubank · Flávio"), sem rótulo de origem. Escolher preenche conta, categorias, tags e pessoa e também o **tipo**, que as categorias exigem (fora do texto do ticket 22, que não fala dele). Valor, data e descrição ficam como estavam. Se a escolha deve completar a descrição é decisão do dono, no [ticket 100](100-escolher-a-sugestao-completa-a-descricao.md).
- **Nome no código**: o que o ticket 22 chama de "pacote" é a `Sugestao` no contrato, como no `GLOSSARY.md`, para não confundir com o "pacote para lançar".
- **Testes**: `backend/tests/test_sugestao.py` (API) e `web/e2e/sugestao.spec.ts` (navegador, com a rede desligada e religada).
- **Reserva**: commitada na própria branch de trabalho, como nos tickets 41, 42 e 44.
- **Pendências**: tickets [100](100-escolher-a-sugestao-completa-a-descricao.md) e [101](101-sugestao-no-aparelho-ate-o-indice-ser-buscado-de-novo.md), e uma linha nova no [35](35-teste-nos-dois-celulares.md) (sugestão nos celulares e o índice no DSQL).
