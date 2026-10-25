# Sincronização offline e conflitos

Type: grilling
Status: claimed
Blocked by: 08, 09, 12
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Issue: #62
Origem: fog "Sincronização offline e conflitos" do [mapa V1 que substitui o Mobills](../map.md), graduado agora que a plataforma ([ticket 08](08-plataforma-do-cliente.md)), o banco ([ticket 09](09-banco-de-dados-e-regiao.md)) e a arquitetura na AWS ([ticket 12](12-como-o-app-roda-na-aws.md)) estão decididos

## Question

Como um lançamento feito sem internet chega ao servidor, e o que acontece quando os dois editam o mesmo lançamento?

Cobrir: o que funciona sem internet (só criar lançamento ou também editar, confirmar previstos, apagar, mexer em regras e planejamento); o que o app guarda no aparelho para ler sem internet; quando e como a fila é enviada (no iPhone só com o app aberto); identidade do lançamento criado offline; o que o usuário vê enquanto algo não foi enviado; o que acontece quando os dois mexem no mesmo lançamento, e com apagar contra editar; geração de previstos por regra feita offline; como "quem criou e quem alterou por último" se registra.

## Checklist

- [ ] Decisão registrada em `## Answer`
- [ ] Vocabulário novo no `GLOSSARY.md` e ADR para o que for difícil de reverter
