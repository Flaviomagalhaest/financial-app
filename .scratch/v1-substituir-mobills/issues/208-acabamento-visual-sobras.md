# Acabamento visual, sobras da primeira rodada

Type: task
Status: resolved
Blocked by: 204
Skills: `implement`, `run`; apoio: `artifact-design` se precisar mostrar opção ao dono
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #542
Origem: revisão (code-review, eixos Standards e Spec) do [ticket 204](204-acabamento-visual-do-app.md). O que ficou de fora da primeira rodada por tamanho ou por não ser decisão tomada no grilling.

## O que falta

- **Favoritos (Configurações)**: cada linha ainda mostra ↑, ↓ e Remover (`web/src/configuracoes/TelaDeFavoritos.tsx`). Levar para o padrão do ⋯ ou para arrastar, sem perder o funcionamento só com internet.
- **Resumo da fatura**: a lista de rótulo e valor ficou compacta, mas ainda tem nove linhas, e Situação e Total repetem a faixa. Avaliar recolher o detalhe ("Ver o detalhe da fatura").
- **Tokens no `estilo.css`**: cerca de 26 `border-radius` literais (0.5rem, 0.5625rem, 0.875rem, 1.25rem) convivem com `--raio-*`; trocar pelos tokens. A folha tem duas definições de `.tabela` (anteriores ao 204) a juntar.
- **Testes e2e**: o 204 inseriu cerca de 60 linhas `getByLabel(`Mais ações ${x}`).click()` antes da ação; um ajudante `pelaLinha(linha, titulo, acao)`, como `web/e2e/conta.ts`, junta o passo.
- **Novo lançamento sem aba marcada**: por decisão (Q14), o + some dentro do lançamento e nenhuma aba fica ativa; se o dono estranhar, marcar a aba de onde veio.

## Checklist

- [x] Favoritos no padrão de linha do app
- [x] Resumo da fatura sem repetir a faixa
- [x] `border-radius` só por token; `.tabela` numa definição
- [x] Ajudante dos testes para o ⋯
- [x] Specs e verificações verdes; PR para `main`
- [ ] Capturas antes e depois: não tiradas nesta sessão (sem navegador autenticado para o app); o dono confere no preview do PR

## Resolução

- Favoritos: ↑/↓/Remover viraram Subir/Descer/Remover dentro do ⋯ (`MenuDeAcoes`), desligados sem internet.
- Fatura: Situação e Total saíram do resumo (a faixa já mostra); o resumo fica em "Ver o detalhe da fatura", recolhido.
- CSS: todos os `border-radius` por token (`--raio-1` a `--raio-10`, mais os três antigos); `.tabela` numa definição só.
- Testes: `pelaLinha(linha, titulo, nome, papel?)` em `web/e2e/conta.ts` substitui 46 pares de linhas; 23 ocorrências de `Mais ações` ficaram porque a ação não segue o par direto.
- Q14 (aba do Novo lançamento) segue como decisão do dono: nada a fazer até estranharem.
