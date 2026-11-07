# Desfazer da edição em lote pula só a parte cuja classificação mudou

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #514
Origem: [ticket 191](191-desfazer-do-lote-nas-partes.md): decisão do dono (07/11) sobre o desfazer da edição em lote nas partes ([ADR 0022](../../../docs/adr/0022-partes-da-compra.md), adendo do ticket 191)

## O que construir

Hoje o desfazer de uma edição em lote volta a compra com partes inteira ou a pula inteira, e qualquer mudança no campo `partes` depois do lote (até só a descrição ou o valor de uma parte) pula a compra. Passa a ser **por parte**:

- **Volta** cada parte que o lote mudou e que ainda tem as categorias e as tags que o lote deu. Mudar a descrição, o valor, a pessoa ou a ordem das partes depois do lote não impede o desfazer.
- **Pula só a parte** cujas categorias, tags ou item mudaram depois do lote (`mudou_depois`), a parte apagada depois (`excluido`) e a parte cuja categoria ou tag de antes do lote foi juntada a outra ou excluída (`saiu`). As outras partes da compra voltam.
- **A parte criada depois do lote** fica como está e não aparece na lista dos pulados.
- **A compra que perdeu todas as partes** depois do lote é pulada inteira (`mudou_depois`), como hoje. A compra excluída continua pulada inteira (`excluido`).
- A mesma regra vale nas partes do parcelamento e nas partes próprias de uma parcela ("só esta").
- **Resposta**: o `PuladoNoDesfazer` ganha `parte_id` e `parte_descricao` (vazios quando o pulado é a compra inteira; `parte_descricao` vazia na parte apagada, porque o lote não guarda a descrição dela). Quem mudou ou apagou, e quando, vêm da versão do campo das partes. A compra conta em `desfeitos` se pelo menos uma parte dela voltou.
- **Tela das edições em lote**: uma linha por parte pulada, "Compra › Parte: motivo"; a parte apagada aparece como "Compra › parte apagada por X".

## Checklist

- [ ] Teste de API: parte reclassificada depois do lote é pulada e as outras partes da mesma compra voltam
- [ ] Teste de API: descrição, valor, pessoa ou ordem das partes mudados depois do lote não impedem o desfazer
- [ ] Teste de API: parte apagada (`excluido`), parte com categoria de antes juntada ou excluída (`saiu`), parte criada depois (fica de fora) e compra que perdeu todas as partes (pulada inteira)
- [ ] Teste de API: a mesma regra no parcelamento com partes e na parcela com partes próprias
- [ ] Teste de API: `desfeitos` conta a compra com pelo menos uma parte de volta; o pulado traz `parte_id`, `parte_descricao`, quem e quando
- [ ] Implementar no servidor e regenerar o `openapi.json` e o schema do app
- [ ] Tela: a parte pulada aparece com o nome da compra e da parte, com spec
