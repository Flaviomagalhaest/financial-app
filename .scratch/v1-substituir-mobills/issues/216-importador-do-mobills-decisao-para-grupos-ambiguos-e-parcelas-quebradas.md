# Importador do Mobills: decisão para grupos ambíguos e parcelas quebradas

Type: task
Status: claimed
Blocked by: —
Skills: `grilling` (HITL: o dono diz o que decide em cada aba), `domain-modeling` se surgir termo novo; depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #566
Origem: [ticket 92](92-rodar-o-importador-nos-exports-reais.md) (o dono rodou o importador nos exports reais e disse que as abas `Grupos ambíguos` e `Parcelas quebradas` precisam de uma coluna de decisão; hoje só informam)

## O que construir

Nos exports reais, a aba `Grupos ambíguos` tem 26 linhas (13 grupos) e a `Parcelas quebradas` tem 342 sequências (216 com cartão, 126 sem; 337 com parcela faltando e 16 com parcela duplicada no mês). As duas só informam: o ticket 18 manda o grupo e a sequência "para a revisão" sem dizer o que o dono decide.

Sessão de `grilling` com o dono para fechar:

- o que ele decide em cada linha (nos grupos ambíguos: casar de outro jeito, separar? nas parcelas quebradas: gerar as que faltam, deixar avulsas, juntar a duplicada?);
- se os 342 são esperados (compras lançadas como parcela em meses fora dos exports, parcelas de 2026-09 em diante que ainda não chegaram) ou sinal de problema em `parcelas.py`: 79 têm falta só no fim, 101 só no começo e 157 nos dois lados;
- como a decisão volta ao importador (colunas na própria aba, como as outras abas, mantidas nas rodadas seguintes).

## Checklist

- [ ] Decisões por aba registradas (grilling)
- [ ] Coluna de decisão nas abas e o importador lê e mantém a decisão
- [ ] Teste: a decisão muda o resultado do cruzamento ou do parcelamento e sobrevive a uma nova rodada
- [ ] Se os 342 forem sinal de problema, diagnosticar `parcelas.py` num ticket à parte
