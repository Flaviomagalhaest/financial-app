# Escolher a sugestão completa a descrição?

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling`, `domain-modeling`; HITL (decisão do dono); depois `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #191
Origem: [ticket 63](63-sugestao-pelo-historico.md): escolher uma sugestão preenche conta, categorias, tags e pessoa e deixa a descrição como foi digitada, porque o [ticket 22](22-sugestao-automatica-de-categorias-e-tags.md) e o `GLOSSARY.md` (**Sugestão**) só falam desses campos

## O que decidir

Quem digita "sa" e escolhe a sugestão "Sacolão São Jorge" salva o lançamento com a descrição "sa". Ele aparece assim no histórico e vira uma descrição curta a mais no índice de sugestão. Escolher deveria trocar a descrição digitada pela da sugestão?

## Checklist

- [x] Decidir com o dono uma das saídas e ajustar o termo **Sugestão** no `GLOSSARY.md`:
  - escolher completa a descrição com a da sugestão (sem a parcela `(n/total)`);
  - escolher completa só quando o digitado é o começo da descrição da sugestão (igual ou "começa com"), e mantém o digitado quando casou por uma palavra do meio;
  - nada muda (hoje é este o comportamento)
- [x] Implementar a saída escolhida em `escolher` (`web/src/lancamentos/TelaDeLancamento.tsx`), com o teste de navegador em `web/e2e/sugestao.spec.ts`
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

Recomendação do agente do ticket 63: a segunda saída. Ela completa o caso comum (digitar o começo) e não troca a descrição quando o casamento foi por uma palavra do meio, em que o digitado pode ser outra coisa.

## Decisão

Decidido pelo dono: a segunda saída (completa só quando o digitado é o começo da descrição da sugestão). Teste de navegador escrito, mas não rodado na sessão (sem Postgres).
