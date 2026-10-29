# Sugestão pelo histórico

Type: task
Status: claimed
Blocked by: 42
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #117
Origem: [spec da v1](../spec.md), etapa 6; histórias de usuário 38, 39, 40, 41, 42, 43

## O que construir

Ao digitar a descrição, o app oferece categorias, tags, conta e pessoa de um lançamento parecido, sem internet ([ticket 22](22-sugestao-automatica-de-categorias-e-tags.md)).

## Checklist

- [ ] Contrato de fonte de sugestão (entrada: descrição e contexto; saída: pacotes com origem); a v1 entrega só a fonte "histórico", que no servidor produz o índice levado ao aparelho no pacote para lançar
- [ ] Casamento no aparelho: igual, começa com, palavra que começa com; sem acento e maiúscula e sem `(n/total)`; a partir de 2 letras, até 3 pacotes, do mais recente ao mais antigo
- [ ] Escolher preenche os campos e mantém o valor; corrigir as categorias torna essa a sugestão mais recente
- [ ] Testes de API do índice e de navegador sem internet
- [ ] Verificações do projeto rodando e PR aberto para `main`
