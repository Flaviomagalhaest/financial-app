# Limites de resposta da Lambda, da HTTP API e do CloudFront, e se comprimir a lista resolve

Origem: [ticket 124](../issues/124-historico-sem-a-lista-inteira.md) (checklist: "Confirmar com `research` o limite de resposta da Lambda e da HTTP API e se comprimir a resposta ajuda"). Números da lista: [ticket 123](../issues/123-historico-com-o-volume-real.md).

Data de acesso de todas as fontes: **2026-11-02**. Fontes primárias da AWS (guias da Lambda, da API Gateway e do CloudFront, referência da API do CloudFront e do CDK) e o código do repositório e das bibliotecas instaladas. Onde a fonte oficial não diz, está escrito "não encontrado na fonte oficial". Itens marcados **[inferência]** são conclusão minha a partir das fontes; **[medido]** é número que eu medi nesta sessão (método na seção 4). Cada afirmação traz o código da fonte `[Sx]` (documentação) ou `[Cx]` (código), listadas no fim.

Unidades: a Lambda escreve "MB" querendo dizer 1.024 KB `[S1]`, ou seja, **6 MB = 6 MiB = 6.291.456 bytes**. O `medir-historico.ts` também divide por 1024² `[C5]`, então os "7,3 MB" do ticket 123 são MiB (cerca de 7,65 milhões de bytes, uns **696 bytes por lançamento**). O CloudFront fala em bytes decimais (10.000.000) `[S9]`.

---

## Resumo para a decisão

- **Comprimir resolve o limite da Lambda, com folga.** Com gzip feito na própria FastAPI (o `GZipMiddleware` do Starlette) a Lambda devolve o corpo em base64, e o limite de 6 MiB passa a valer para o gzip inflado em 4/3. A lista de 11 mil lançamentos cai de cerca de 10 MB de envelope para **1,1 a 1,7 MB** **[medido]**. Cabem uns **39 mil a 63 mil lançamentos**, ou seja, **28 a 45 anos** de histórico a 1.400 por ano (20 a 37 anos além dos 11 mil de hoje) **[inferência a partir do medido]**.
- **Sem compressão o limite chega antes do que o ticket estimou.** O `body` vai como texto JSON dentro do JSON de resposta da Lambda, e cada aspas vira `\"`: o envelope fica uns **12% maior** que a lista **[medido]**. O teto fica perto de **7.900 lançamentos** (não 8.500), uns 5,6 anos de histórico. Os 11 mil de hoje já passam.
- **O CloudFront não ajuda nesse limite.** Ele comprime depois da origem, e o comportamento `/api/*` usa a política `CachingDisabled`, com a qual o CloudFront não comprime nada `[S11][S14]`. A HTTP API também não comprime: a compressão da API Gateway (`minimumCompressionSize`) só existe na REST API `[S8]`.
- **Streaming não é opção na HTTP API.** A HTTP API não tem streaming de resposta `[S5][S3]`. Só a URL de função e a REST API têm, até 200 MB, e para Python só com runtime próprio ou com o Lambda Web Adapter `[S2]`. Trocar mexe no ADR 0010.
- **O que a compressão não resolve:** o render e o layout de milhares de itens e a gravação no IndexedDB (a maior parte dos 4,8 a 16,5 s do ticket 123). O navegador descomprime antes do `response.json()`, então o JSON que o app lê e guarda é o mesmo. **[inferência]** A compressão tira só o bloqueio duro de "a lista inteira nem chega". Com ela, o caminho 3 do ticket (virtualização com a lista inteira) fica possível do lado do servidor, mas continua sem resolver a gravação no aparelho.

---

## 1. Como a Lambda é chamada hoje (código)

- **Integração Lambda proxy da HTTP API, formato 2.0.** `HttpLambdaIntegration("Lambda", api)` sem `payloadFormatVersion` `[C1]`, e o padrão do CDK é `PayloadFormatVersion.VERSION_2_0` `[S15]`. As rotas são `GET /api/saude` (sem login) e `ANY /api/{proxy+}` (JWT) `[C1]`.
- **Invocação síncrona e com buffer.** Não há URL de função, `InvokeWithResponseStream` nem `responseTransferMode` no código `[C1]`. A HTTP API não tem streaming `[S5]`.
- **Timeouts:** a Lambda tem 29 s (comentário: "a HTTP API corta em 30 s") e a integração usa o padrão do CDK, 29 s `[C1][S15]`. O máximo da HTTP API é 30 s `[S6]`.
- **Adaptador:** `Mangum(create_app(), lifespan="off")` `[C2]` (Mangum 0.22.0 no `uv.lock`). Para o formato 2.0, o Mangum devolve `{"statusCode", "headers", "body", "cookies", "isBase64Encoded"}`. O corpo vai como **texto** quando o `content-type` está na lista de tipos de texto (inclui `application/json`) e decodifica como UTF-8. Senão, ou se a decodificação falhar, vai em **base64** com `isBase64Encoded: true` `[C3]`.
- **Sem compressão na API:** não há `GZipMiddleware` nem outro `gzip` na `backend/app` (o único `compress` é o zip do backup) `[C1][C2]`.

## 2. Lambda: limite da resposta síncrona e streaming

- **6 MB (6 MiB) para o pedido e 6 MB para a resposta, na invocação síncrona.** Continua assim na página de cotas de hoje, e não pode ser aumentado `[S1]`. A invocação assíncrona é 1 MB `[S1]`.
- **O que conta nos 6 MB:** a página de cotas diz só "invocation payload (request and response)" `[S1]`. Que o número conta o JSON serializado do envelope (o `body` escapado ou em base64, mais `headers` e `statusCode`), e não só o corpo HTTP, **não encontrado na fonte oficial**. **[inferência]** É o que acontece, porque o "payload" da resposta da Lambda é o valor que a função devolve, serializado. Num fórum não oficial, uma função Python que devolvia uma string de 7.165.488 bytes recebeu "Response payload size (8198440 bytes) exceeded maximum allowed payload size (6291556 bytes)", ou seja, +14% depois de serializar `[S18]`. É coerente com o escape medido aqui (+12%, seção 4).
- **Streaming de resposta:** até **200 MB** por resposta; os primeiros 6 MB sem limite de banda, o resto a 2 MB/s `[S1][S2]`. Funciona pela **URL de função**, pela API `InvokeWithResponseStream` e pela **integração proxy da API Gateway** `[S2]`, e esta última **só na REST API** (`responseTransferMode: STREAM`) `[S3][S4][S5]`. A Lambda tem streaming nativo **só nos runtimes Node.js gerenciados**. Em Python, só com runtime próprio ou com o Lambda Web Adapter `[S2]`.
- Com streaming na REST API, a API Gateway **não comprime** ("Content encoding" fica de fora; "comprima na integração"), e o stream pode durar até 15 min `[S3]`.
- A página de cotas agora lista também as "Lambda Web Functions" (servidor HTTP com timeout de pedido de até 900 s) `[S1]`. Não pesquisei esse produto: ele não estava no ADR 0010.

## 3. HTTP API: limites e compressão

- **Timeout máximo da integração: 30 s**, não aumentável `[S6]`.
- **"Payload size": 10 MB**, não aumentável `[S6]`. A página não diz se o número vale para o pedido, para a resposta ou para os dois, nem se conta o corpo antes ou depois de decodificar o base64: **não encontrado na fonte oficial**. **[inferência]** Para este app não importa, porque os 6 MiB da Lambda chegam antes.
- **Compressão da resposta: a HTTP API não tem.** A compressão por `minimumCompressionSize` (0 a 10.485.760 bytes) está documentada como "Payload compression for REST APIs" `[S8]`, e a tabela REST × HTTP não lista compressão para a HTTP API `[S5]`. Que a HTTP API não comprime, com essas palavras, **não encontrado na fonte oficial**: é **[inferência]** pela ausência.
- **Base64 na resposta:** o formato 2.0 aceita `isBase64Encoded: true|false` na resposta da Lambda `[S7]`. Segundo o blog de computação da AWS (2021), a HTTP API "usa o `isBase64Encoded` para decodificar o texto antes de devolver a resposta" e não precisa configurar tipos binários `[S17]`. O guia da HTTP API mostra o campo, mas não descreve a decodificação com essas palavras `[S7]`.
- **`Content-Encoding` vindo da Lambda:** que a HTTP API repassa ao cliente o `content-encoding: gzip` devolvido pela função sem mexer, **não encontrado na fonte oficial**. **[inferência]** Repassa: os cabeçalhos da resposta 2.0 vão ao cliente, e a HTTP API não tem compressão própria que pudesse conflitar. **Precisa ser conferido no `dev`** antes de contar com isso (seção 6).

## 4. A própria Lambda comprimindo: medida

**Método [medido].** O banco não estava disponível na sessão. Gerei os lançamentos em Python com o mesmo padrão do gerador do ticket 112 (`backend/medir_busca.py`: 14 descrições, 4 contas, 40 categorias, tag em 1 de cada 4, 2% previstos, 95% `fonte: mobills`, e parcelamentos de 5). Para cada tamanho, 10.600 avulsos e 80 parcelamentos dão 11 mil. Os itens são objetos `app.lancamentos.Lancamento` reais, serializados por uma rota FastAPI com `response_model=list[Lancamento]`, como `GET /api/lancamentos`. Depois passei a lista de 11 mil pelo **Mangum 0.22.0** num evento HTTP API 2.0 (como `app/lambda_handler.py`), com e sem `GZipMiddleware`, e medi `json.dumps` do valor que a Lambda devolveria. Para não superestimar a compressão, fiz uma segunda amostra **pessimista**: os mesmos 11 mil itens com descrição aleatória (1 a 4 palavras de um vocabulário de 3 mil), valor aleatório, 120 categorias, 12 contas e `criado_em`/`alterado_em` aleatórios com microssegundos.

A minha amostra dá 814 bytes por item, contra uns 696 do ticket 123. O esquema é o mesmo, e a diferença deve vir dos dados gerados. Por isso uso **bytes por item** e a **razão de compressão**, não o total em MB.

| 11 mil lançamentos | Amostra do gerador (repetitiva) | Amostra pessimista |
|---|---|---|
| Lista JSON (corpo HTTP) | 8.956.966 B (814 B/item) | 9.275.146 B (843 B/item) |
| Envelope da Lambda **sem** gzip (corpo como texto, aspas escapadas) | 10.029.507 B (**+12%**, 912 B/item) | não medido (mesmo esquema: uns +96 B/item de escape) |
| gzip nível 6 | 846.573 B (10,6×) | 1.292.447 B (**7,2×**, 117 B/item) |
| gzip nível 9 (padrão do `GZipMiddleware`) | 818.591 B (**10,9×**) | não medido |
| Envelope da Lambda **com** `GZipMiddleware` + base64 (Mangum) | **1.091.644 B (99 B/item)** | ~1.723.000 B (157 B/item, gzip 6 × 4/3) |

- **[medido]** Com `GZipMiddleware` e `Accept-Encoding: gzip` no pedido, o Mangum tenta decodificar o gzip como UTF-8, falha e devolve `isBase64Encoded: true` com `content-encoding: gzip`, sem configuração nenhuma `[C3][C4]`. Conferi que `gzip.decompress(base64(body))` devolve a lista original. Sem `Accept-Encoding` o middleware não comprime, e o envelope volta aos 10 MB.
- **[medido]** Tempo do gzip da lista de 11 mil (8,96 MB) num x86 de 4 núcleos: 48 ms no nível 1, 121 ms no 6 e 211 ms no 9. **[inferência]** Na Lambda de 512 MB (ARM, fração de vCPU) deve ficar algumas vezes mais lento, ainda dentro de 1 a 2 s para 11 mil, longe dos 29 s. O nível 6 dá quase o mesmo tamanho por metade do tempo.
- O `GZipMiddleware` do Starlette 1.10.0 comprime a partir de 500 bytes, no nível 9 por padrão, e só quando o pedido aceita gzip `[C4]`.

**Quanto cabe nos 6 MiB (6.291.456 B) [inferência a partir do medido]:**

| | Bytes por lançamento no envelope | Teto de lançamentos | Anos a 1.400/ano |
|---|---|---|---|
| Sem compressão (hoje), dados do ticket 123 | ~696 + ~96 de escape ≈ 792 | **~7.900** | ~5,6 |
| Sem compressão, sem contar o escape (conta do ticket) | ~696 | ~9.000 | ~6,4 |
| gzip + base64, amostra pessimista | ~157 | **~40.000** | **~28** |
| gzip + base64, amostra do gerador | ~99 | **~63.000** | **~45** |

O tamanho comprimido depende do que muda de um item para outro (ids aleatórios, valores, datas, descrições), não dos nomes dos campos. Por isso uso a faixa medida, sem reescalar pelos 696 bytes. Os ids são UUID aleatórios, e só os 5 ids de cada item (o dele, a conta, a categoria e os dois horários) somam umas dezenas de bytes depois do gzip. **[inferência]** Por isso a razão real não deve passar muito de 10×. A faixa 7× a 11× (os 5 a 10× da pergunta) é a que eu usaria.

## 5. CloudFront: compressão automática e o comportamento `/api/*`

- **Faixa de tamanho:** o CloudFront comprime objetos de **1.000 a 10.000.000 bytes**, e só com `Content-Length` na resposta da origem, status 200/403/404 e um `Content-Type` da lista (`application/json` está nela) `[S9]`. Se a origem já manda `Content-Encoding`, ele não comprime de novo e repassa o comprimido ao cliente `[S9]`.
- **Comprime resposta de API?** O tipo de origem não importa para a documentação. O que importa é o comportamento ter "Compress objects automatically" **e** uma política de cache com Gzip/Brotli ligados `[S9][S10]`. O artigo oficial do re:Post (AWS) diz: "Check that the TTL values in the cache policy are set to a value greater than zero. **CloudFront doesn't compress objects when caching is turned off**" `[S14]`.
- **Ajuda no limite da Lambda? Não.** A compressão do CloudFront acontece na borda, sobre a resposta que já veio da origem `[S9]`. **[inferência]** A Lambda já teria estourado os 6 MiB antes. Ela só reduz o tráfego da borda até o celular. Além disso, a lista inteira de hoje (7,65 MB) fica perto do teto de 10 MB do CloudFront: com uns 14 mil lançamentos, nem isso.

**O que o repositório faz hoje** `[C1]`:

- **Comportamento padrão (PWA no S3):** sem `cachePolicy` e sem `compress`, então valem os padrões do CDK: `CachePolicy.CACHING_OPTIMIZED` e `compress: true` `[S16]`. A política `CachingOptimized` tem compressão ligada `[S11]`, então os arquivos do app saem comprimidos.
- **Comportamento `/api/*`:** `CachePolicy.CACHING_DISABLED`, `OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER`, todos os métodos, `compress` no padrão (`true`) `[C1][S16]`.
  - A `CachingDisabled` tem TTLs 0/0/0 e "Cache compressed objects setting: Disabled" `[S11]`. Com TTL zero o CloudFront não comprime `[S14]`, então o `compress: true` não tem efeito aqui **[inferência]**.
  - Com a compressão da política desligada, o CloudFront trata o `Accept-Encoding` "como qualquer outro cabeçalho" `[S10][S13]`, e a `AllViewerExceptHostHeader` repassa "todos os cabeçalhos do pedido, exceto `Host`" `[S12]`. **[inferência]** O `Accept-Encoding: gzip, deflate, br` do navegador chega à HTTP API e à Lambda, e o `GZipMiddleware` funcionaria sem mudar o CloudFront. A documentação não diz com essas palavras que o `Accept-Encoding` passa nesse caso: **conferir no `dev`**.
  - Se a Lambda devolver `Content-Encoding: gzip`, o CloudFront repassa o comprimido ao navegador `[S9]`.

## 6. O que falta conferir (não encontrado na fonte oficial)

- Se a HTTP API repassa ao cliente o `content-encoding: gzip` da Lambda e decodifica o base64 (o guia mostra o campo `[S7]`; a decodificação está no blog `[S17]`).
- Se o `Accept-Encoding` do navegador chega à Lambda com `CachingDisabled` + `AllViewerExceptHostHeader` (seção 5).
- Se os 6 MiB contam o envelope serializado (a medida e o fórum `[S18]` dizem que sim).
- **[inferência]** Uma chamada com `curl -sS -D- -o /dev/null -H 'Accept-Encoding: gzip' -H "Authorization: Bearer …" https://<cloudfront>/api/lancamentos` no `dev`, com o middleware ligado, responde as três: deve aparecer `content-encoding: gzip`, e o `Content-Length` deve ser o tamanho comprimido.

---

## Fontes

**AWS Lambda**
- `[S1]` "Lambda quotas" (seção "Function configuration, deployment, and execution": invocation payload, streamed responses, nota de MB = 1.024 KB; seção "Lambda Web Functions"). https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html
- `[S2]` "Response streaming for Lambda Event Functions". https://docs.aws.amazon.com/lambda/latest/dg/configuration-response-streaming.html

**Amazon API Gateway**
- `[S3]` "Stream the integration response for your proxy integrations in API Gateway" ("Response streaming is only supported for REST APIs"; sem content encoding; 15 min). https://docs.aws.amazon.com/apigateway/latest/developerguide/response-transfer-mode.html
- `[S4]` "Set up a Lambda proxy integration with payload response streaming in API Gateway". https://docs.aws.amazon.com/apigateway/latest/developerguide/response-transfer-mode-lambda.html
- `[S5]` "Choose between REST APIs and HTTP APIs" (linha "Response streaming": REST sim, HTTP não). https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html
- `[S6]` "Quotas for configuring and running an HTTP API in API Gateway" (timeout de 30 s, payload de 10 MB). https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-quotas.html
- `[S7]` "Create AWS Lambda proxy integrations for HTTP APIs in API Gateway" (formatos 1.0 e 2.0, resposta com `isBase64Encoded`). https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html
- `[S8]` "Payload compression for REST APIs in API Gateway" (`minimumCompressionSize`). https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-gzip-compression-decompression.html

**Amazon CloudFront**
- `[S9]` "Serve compressed files" (1.000 a 10.000.000 bytes, `Content-Length`, origem com `Content-Encoding`, tipos). https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/ServingCompressedFiles.html
- `[S10]` "Understand cache policies" (Compression support; TTLs zerados desligam o cache). https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cache-key-understand-cache-policy.html
- `[S11]` "Use managed cache policies" (`CachingDisabled`, `CachingOptimized`). https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html
- `[S12]` "Use managed origin request policies" (`AllViewerExceptHostHeader`). https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-origin-request-policies.html
- `[S13]` CloudFront API Reference, `ParametersInCacheKeyAndForwardedToOrigin` (`EnableAcceptEncodingGzip`/`Brotli`). https://docs.aws.amazon.com/cloudfront/latest/APIReference/API_ParametersInCacheKeyAndForwardedToOrigin.html
- `[S14]` AWS re:Post Knowledge Center (autor "AWS Official"), "How do I troubleshoot issues with compressing files in CloudFront?", publicado 2022-06-02, modificado 2024-08-19. https://repost.aws/knowledge-center/cloudfront-troubleshoot-compressed-files

**AWS CDK (v2.275.0 na documentação)**
- `[S15]` `HttpLambdaIntegrationProps` (`payloadFormatVersion` padrão `VERSION_2_0`; `timeout` padrão 29 s). https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2_integrations.HttpLambdaIntegrationProps.html
- `[S16]` `BehaviorOptions` (`compress` padrão `true`; `cachePolicy` padrão `CACHING_OPTIMIZED`). https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_cloudfront.BehaviorOptions.html

**Secundárias (não são documentação oficial; só reforçam)**
- `[S17]` AWS Compute Blog, "Handling binary data using Amazon API Gateway HTTP APIs", 2021-03-31. https://aws.amazon.com/blogs/compute/handling-binary-data-using-amazon-api-gateway-http-apis/
- `[S18]` AWS re:Post, pergunta da comunidade "AWS Lambda - Body Size is Too Large Error, but Body Size is Under Limit", 2021-04-05 e resposta de 2021-05-10 (mensagens de erro com 6.291.556 bytes). https://repost.aws/questions/QU57r4NMQIQROXqW4Vl6YDBQ/aws-lambda-body-size-is-too-large-error-but-body-size-is-under-limit

**Código**
- `[C1]` `infra/lib/pilha-app.ts` (Lambda, HTTP API, rotas, distribuição do CloudFront).
- `[C2]` `backend/app/lambda_handler.py` e `backend/app/lancamentos.py` (`listar_lancamentos`, modelo `Lancamento`).
- `[C3]` Mangum 0.22.0, `mangum/handlers/utils.py` (`handle_base64_response_body`) e `mangum/handlers/api_gateway.py` (resposta do formato 2.0).
- `[C4]` Starlette 1.10.0, `starlette/middleware/gzip.py` (`minimum_size=500`, `compresslevel=9`). A página https://www.starlette.io/middleware/ não abriu nesta sessão (domínio fora da rede permitida); usei o código instalado pelo `uv.lock`.
- `[C5]` `web/e2e/medir-historico.ts` (tamanho da lista em `bytes / 1024 / 1024`).
