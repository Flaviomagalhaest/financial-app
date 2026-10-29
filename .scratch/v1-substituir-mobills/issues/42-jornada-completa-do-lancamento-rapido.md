# Jornada completa do lançamento rápido

Type: task
Status: resolved
Blocked by: 36, 40, 41
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #96
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 10-19, 22, 23, 24

## O que construir

A tela de lançar chega ao desenho dos protótipos: lançar uma despesa leva poucos segundos. A fonte de verdade da interface é a variante A da branch `prototipo/lancamento-rapido`.

## Checklist

- [x] Tela de transferência entre duas contas, com categoria opcional da lista de transferência (API do [ticket 36](36-contas-saldo-e-transferencia.md), `/api/transferencias`)
- [x] Fileiras de toque para conta ou cartão e categorias; folha de detalhes com descrição, tags, pessoa, data, parcelado e recorrente (os dois últimos ficam desativados até seus tickets: o recorrente no [86](86-recorrencia-criar-pela-tela-e-sem-internet.md), sobre a API do 44, e o parcelado no [46](46-parcelamento-criar.md)), e resumo numa linha
- [x] Data entre hoje, ontem ou outra; data futura nasce prevista e passada ou de hoje nasce realizada, trocável à mão
- [x] "Repetir último" enquanto o lançamento está vazio
- [x] Atalho "Novo lançamento" funcionando no Android e botão na tela inicial no iPhone
- [x] Teste de navegador do fluxo completo, online e offline
- [x] Verificações do projeto rodando e PR aberto para `main`
- [x] Da revisão do ticket 32: data com "hoje / ontem / outra" (história 18) e a linha de resumo dos detalhes embaixo do valor (história 17); hoje a data é só um campo em "Detalhes"

## Notas da implementação

- **Tela de lançar** (`TelaDeLancamento.tsx`, variante A): tipo no topo, valor, a linha de resumo ("Detalhes: Jantar · #viagem · Flávio · ontem · previsto"; a data de hoje e o realizado não aparecem), "Repetir último", fileiras de conta e de categorias que rolam de lado, teclado e Salvar. A folha de detalhes (`FolhaDeDetalhes.tsx`) é um `<dialog>` modal: descrição, tags, pessoa, data, situação e "Repete?" (Parcelado e Recorrente desativados até os tickets [46](46-parcelamento-criar.md) e [86](86-recorrencia-criar-pela-tela-e-sem-internet.md)). Ela fecha por "Pronto", Esc ou toque fora.
- **Data** (`EscolhaDaData.tsx`): Hoje, Ontem e o campo "Outra data", no dia de São Paulo (`diaAnterior`, `rotuloDaData` em `datas.ts`). A situação segue a regra que já existia: data futura nasce prevista, a escolha à mão vale.
- **Tags**: escolher e criar na folha, pelo nome. A tag nova nasce no servidor junto com o lançamento, então funciona sem internet. As opções (`useTags` em `dados/`) são as do servidor não arquivadas mais as dos lançamentos do aparelho, para a criada sem internet já aparecer no próximo. O Histórico passou a mostrar as tags na linha.
- **Repetir último**: aparece no lançamento novo enquanto não há valor nem categoria. Preenche tipo, valor, conta, categorias ativas, descrição, tags e pessoa, com a data de hoje. O "último" é o mais recente criado à mão por quem está com o aparelho (o não enviado conta e o gerado pela recorrência não), não o da outra pessoa.
- **Transferência** (`TelaDeTransferencia.tsx`): "Transferência" é a terceira opção do seletor de tipo do lançamento novo; o protótipo não tinha tela de transferência. Valor pelo mesmo teclado (segue ao trocar de tipo), De, Para (sem a conta de origem), categoria opcional da lista de transferência, descrição e data. Grava por `criarTransferencia` (`POST /api/transferencias`, id gerado na tela); sem internet a tela avisa e não salva ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)). A situação vem da data, sem troca à mão (linha no [ticket 80](80-transferencia-prevista-atrasada-e-confirmacao.md)).
- **Atalho e botão**: o manifesto já tinha o atalho para `/#/novo` e a Hoje, o "+ Novo lançamento". O teste novo abre `/#/novo` sem internet com o app instalado, como o atalho do Android.
- **Testes**: `web/e2e/jornada.spec.ts`. Os testes antigos fecham a folha com "Pronto" antes de Salvar. Ajustes em testes de outras telas que falhavam por corrida: esperar a mudança da outra pessoa subir em `conflito.spec.ts` e desfazer a rota em `sem-internet.spec.ts`.
- **Desvios do protótipo A**: a data no resumo é `dd/mm/aaaa`, como no Histórico, e não "sex 23/out". Não há ícone 💳 nas fichas, porque cartão ainda não existe (linha no [ticket 37](37-cartoes-e-faturas.md)). O aviso de planejamento fica para o [ticket 52](52-aviso-de-planejamento-ao-lancar.md).
- **Tags na folha**: este ticket fez o primeiro item do [ticket 78](78-telas-de-tags-e-manutencao.md).
- **Reserva**: commitada na própria branch de trabalho, como nos tickets 41 e 44.
- **Pendências**: [88](88-teste-instavel-do-envio-perdido-sem-internet.md) (teste instável do envio perdido); linhas novas nos tickets [35](35-teste-nos-dois-celulares.md) (o dono confere a jornada no celular e as escolhas acima), [37](37-cartoes-e-faturas.md) e [80](80-transferencia-prevista-atrasada-e-confirmacao.md).
