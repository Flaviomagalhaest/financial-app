# Exportação

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #73
Origem: fog "Exportação" do [mapa V1 que substitui o Mobills](../map.md), graduado agora que o banco ([ticket 09](09-banco-de-dados-e-regiao.md)), a arquitetura na AWS ([ticket 12](12-como-o-app-roda-na-aws.md)) e a importação do histórico ([ticket 18](18-importacao-do-mobills-cartao-e-datas.md)) estão decididos

## Question

Qual o formato e o conteúdo da exportação completa do app, que também é o backup diário e precisa poder ser importada de volta num banco novo?

Pontos a decidir:

- o formato do backup (por exemplo, um arquivo só com todas as tabelas ou um arquivo por tabela) e o do CSV para o casal abrir numa planilha, e se são o mesmo arquivo ou dois;
- o que entra: lançamentos com categorias, tags, pessoa e quem criou e alterou por último, contas, cartões, faturas, regras de recorrência e parcelamento, planejamento, favoritos, filtros salvos, e o que fica de fora (usuários e senhas do Cognito);
- como a importação refaz o banco do zero, sem duplicar e com a versão do formato, e como o teste de restauração do CI ([ADR 0010](../../../docs/adr/0010-app-na-aws-cloudfront-http-api-e-uma-lambda.md)) a usa;
- como o "exportar tudo" do app roda (no servidor, com o histórico de 7 anos) e entrega o arquivo ao aparelho;
- a relação com a importação do Mobills ([ADR 0007](../../../docs/adr/0007-historico-do-mobills-cruzado-e-sem-saldo.md)): se o formato do backup serve de formato de entrada para a mesma carga.

## Checklist

- [x] Decisão registrada em `## Answer`
- [x] Vocabulário novo no `GLOSSARY.md` e ADR para o que for difícil de reverter
- [x] Linha em "Decisions so far" do mapa e item removido de "Not yet specified"

## Answer

Decidido com o dono em 2026-10-27. Um só gerador de exportação atende o backup diário, o botão "exportar tudo" do app e a carga do histórico.

- **Dois formatos, uma leitura do banco**: o **backup** é um `.zip` com um CSV por tabela e um `manifesto.json`; o **CSV da planilha** é um arquivo só de lançamentos, com nomes no lugar dos ids. O CSV da planilha usa `;` como separador, vírgula decimal, datas `AAAA-MM-DD` e UTF-8 com BOM, e traz data, descrição, valor, conta ou cartão, fatura, categorias (separadas por ` | `), tags, pessoa, situação (previsto ou efetivado) e quem criou e alterou por último. Filtro por período fica para depois.
- **O que entra no backup**: tudo o que é dado do casal, com os ids originais: lançamentos (categorias, tags, pessoa, quem criou e alterou por último e quando), contas, cartões, faturas, regras de recorrência e parcelamento, planejamento, favoritos, filtros salvos e saldos de abertura. Ficam de fora usuários, senhas e tokens do Cognito e a fila offline do aparelho; guarda-se só o identificador da pessoa (o `sub` do Cognito ou o nome) para religar quem criou cada lançamento.
- **Restauração**: só roda em banco vazio (recusa banco com dados, e é assim que não duplica), numa carga única "tudo ou nada" na ordem das chaves, e confere ao final as contagens e somas por tabela contra o manifesto. O manifesto leva `versao_formato`; a importação recusa versão desconhecida, e o código mantém conversores das versões antigas. Não existe mesclagem.
- **Como o "exportar tudo" roda**: `POST /api/exportacoes` faz a Lambda gerar o zip (ou o CSV), gravar num prefixo do S3 e devolver uma URL assinada de 5 minutos; o app abre a URL. Os arquivos sob demanda ficam num prefixo separado do backup diário, com expiração de 7 dias. Qualquer um dos dois pode exportar, e cada pedido é registrado (quem e quando) numa tabela do banco, que entra no backup como as outras.
- **Backup diário**: o EventBridge chama a mesma função geradora, que grava no S3 com versões e Object Lock de 90 dias ([ADR 0010](../../../docs/adr/0010-app-na-aws-cloudfront-http-api-e-uma-lambda.md)). Antes de dar o dia por feito, a função abre o zip e compara as contagens com o banco. Um alarme do CloudWatch avisa por e-mail (SNS) se o backup falhar ou não rodar em 26 horas.
- **Teste de restauração do CI**: restaura num banco vazio de teste um backup de exemplo fictício, versionado no repositório, exporta de novo e exige zip idêntico (ida e volta sem perda); um segundo teste restaura um backup de versão antiga para provar os conversores. Dado real nunca vai ao CI.
- **Entrega no iPhone**: melhor esforço, abrindo a URL assinada (o iOS mostra o arquivo para salvar). O backup diário no S3 é a rede de segurança; se a entrega falhar no iOS, não bloqueia a v1 ([ticket 26](26-verificar-o-download-da-exportacao-no-iphone.md)).
- **Relação com o Mobills** ([ADR 0007](../../../docs/adr/0007-historico-do-mobills-cruzado-e-sem-saldo.md)): o app não volta a usar o Mobills; a pergunta era só como a carga única do histórico grava. O importador do Mobills gera um backup válido e a restauração o grava, então há um só caminho de carga em massa, já coberto pelo teste do CI.

Termos novos no [glossário](../../../GLOSSARY.md): **Backup**, **Exportação** e **Restauração**. ADR: [0012](../../../docs/adr/0012-exportacao-unica-zip-de-csvs-e-restauracao-so-em-banco-vazio.md). Pendência no tracker: [ticket 26](26-verificar-o-download-da-exportacao-no-iphone.md).
