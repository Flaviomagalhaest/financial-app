# Sugestão automática de categorias e tags

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #64
Origem: item "Sugestão automática de categorias e tags" de "Not yet specified" do mapa, que o [ticket 10](10-fluxo-de-lancamento-rapido.md) deixou pronto para especificar (a folha de detalhes tem a descrição com sugestão pelo histórico)

## Question

De onde vem a sugestão de categorias e tags quando o casal digita a descrição de um lançamento, e como ela aprende com o uso?

## Checklist

- [x] Fonte da sugestão e como ela aprende, decididas com o dono, em `## Answer`
- [x] Termos **Sugestão** e **Fonte de sugestão** no `GLOSSARY.md`

## Answer

A sugestão vem de uma **busca no histórico do próprio casal**, sem ML, sem IA e sem serviço externo na v1, e a spec deixa um **encaixe** para fontes futuras (um modelo, uma IA generalista), que podem nunca existir.

- **Sinal**: só o texto da descrição, normalizado (sem acento, sem maiúscula, sem números de parcela como `(2/10)`). Valor e conta não entram.
- **O que é sugerido**: o pacote inteiro de um lançamento anterior (categorias, tags, conta e pessoa), escolhido por inteiro e sem misturar campos de lançamentos diferentes. Escolher preenche tudo e mantém o valor digitado ([ticket 10](10-fluxo-de-lancamento-rapido.md)).
- **Casamento**: descrição igual, depois "começa com", depois "contém uma palavra que começa com" o que foi digitado, nessa prioridade. Sem tolerância a erro de digitação na v1. Sem casamento, a lista fica vazia, sem substituto.
- **Aprendizado**: não há treino. Cada lançamento salvo já entra na base. Entre os lançamentos de mesma descrição, as sugestões são os pacotes diferentes, do **mais recente para o mais antigo**, no máximo 3. Corrigir categorias num lançamento o torna o mais recente daquela descrição, então a ordem se corrige sozinha. Um modelo de previsão pode entrar depois como outra fonte.
- **Quando aparece**: a partir de 2 letras, atualizada a cada letra, numa lista curta abaixo da descrição.
- **Rejeitar**: não há "nunca sugerir isso" nem botão de dispensar na v1. Ignorar a sugestão e escolher outro pacote já ensina pela recência. O botão de dispensar fica como ajuste futuro, se incomodar.
- **Sem internet**: roda no aparelho, com um índice leve das descrições (poucos MB) que se atualiza junto com a sincronização. O formato da sincronização é decidido no ticket de offline e conflitos; este ticket só exige que o índice caiba no aparelho e que a sugestão funcione sem rede.
- **Ponto de partida**: o histórico importado do Mobills alimenta a sugestão desde o primeiro dia, com categorias e tags já passadas pelo de-para revisado. Ficam de fora os `Reajuste de fatura` (ajustes de fatura) e as transferências.
- **Encaixe para fontes futuras**: a spec define a sugestão como um contrato com **fontes de sugestão** substituíveis. A entrada é a descrição (mais o contexto do lançamento, se precisar) e a saída é uma lista de pacotes com um campo de **origem**. A v1 entrega só a fonte "histórico" e nenhuma IA nem modelo. Uma fonte nova se soma à do histórico ou a substitui sem mudar a tela nem o formato. O histórico local é sempre o plano B: se a fonte nova falhar ou estiver offline, a sugestão não some.
- **Onde uma fonte futura roda**: só no servidor (logo, só com internet), nunca no caminho crítico do lançamento (a lista do histórico aparece na hora e a da outra fonte completa depois, se chegar). Fica **dentro da conta AWS** do app; nenhum dado financeiro vai para um serviço fora da AWS sem o dono decidir de novo.
- **Origem na tela**: na v1 não aparece rótulo, porque só existe a origem "histórico"; o campo de origem do formato fica para a tela usar quando houver uma segunda fonte.

Sem ADR: a decisão é fácil de reverter (nada além da busca e do contrato de fontes). Vocabulário novo (**Sugestão**, **Fonte de sugestão**) no `GLOSSARY.md`; o **Favorito** passa a falar em "sugeridos" para não confundir.

Fica para a spec: os números 2 letras e 3 sugestões são valores iniciais, a ajustar com o uso; o desenho do índice no aparelho depende do ticket de offline e conflitos.
