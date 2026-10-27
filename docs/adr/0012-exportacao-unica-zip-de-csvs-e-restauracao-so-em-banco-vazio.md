---
status: accepted
---

# Exportação única: zip de CSVs por tabela e restauração só em banco vazio

O backup diário, o "exportar tudo" do app e a carga do histórico do Mobills usam o mesmo formato: um `.zip` com um CSV por tabela, os ids originais e um `manifesto.json` com `versao_formato`, contagens e somas. Uma função geradora só lê o banco; o EventBridge a chama todo dia e `POST /api/exportacoes` a chama a pedido, devolvendo uma URL assinada de 5 minutos. A restauração só roda em banco vazio, numa carga única tudo ou nada, e confere o resultado contra o manifesto. O CSV de lançamentos para planilha é um segundo formato, só de leitura, gerado da mesma consulta.

## Considered Options

- **Um arquivo só para backup e planilha**: o backup precisa de ids e de todas as tabelas, e a planilha precisa de nomes; um arquivo ruim para os dois.
- **JSON único**: difícil de abrir numa planilha em caso de emergência e pesado de carregar de uma vez.
- **Mesclar na restauração**: exigiria regra de conflito por linha; recusar banco não vazio já garante que não duplica.
- **Carga do Mobills com gravação própria**: um segundo caminho de escrita em massa, usado uma vez e fora do teste do CI.

## Consequences

- O importador do Mobills ([ADR 0007](0007-historico-do-mobills-cruzado-e-sem-saldo.md)) gera um backup válido, e a restauração o grava.
- Mudar o esquema exige subir `versao_formato` e manter um conversor da versão anterior; o CI restaura um backup de exemplo atual e outro de versão antiga e exige ida e volta idêntica. Dado real nunca vai ao CI.
- Ficam de fora usuários e senhas do Cognito e a fila offline; guarda-se só o identificador da pessoa.
- O backup diário confere as contagens do zip contra o banco, e um alarme avisa por e-mail se falhar ou não rodar em 26 horas.
- Exportações sob demanda ficam num prefixo do S3 com expiração de 7 dias, separado do backup com Object Lock ([ADR 0010](0010-app-na-aws-cloudfront-http-api-e-uma-lambda.md)).
