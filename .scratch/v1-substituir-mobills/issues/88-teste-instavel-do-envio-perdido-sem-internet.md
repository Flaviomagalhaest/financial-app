# Teste instável do envio perdido sem internet

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #183
Origem: [ticket 42](42-jornada-completa-do-lancamento-rapido.md) (na suíte inteira de navegador, o teste falhou duas vezes e passou sozinho e em repetições)

## O que construir

O teste "criado com a resposta perdida e depois editado ou excluído sem internet: a mudança não se perde" (`web/e2e/sem-internet.spec.ts`) às vezes não acha a linha `Editado <s>` no Histórico. A tela mostra "Sem internet: não foi possível carregar os lançamentos." e a lista vazia. Hipótese: quando a rede volta, o `sync` do service worker reenvia a fila, que o `page.route` da página não intercepta, e a esvazia antes de a lista do servidor ser lida e guardada. Ao voltar a ficar sem internet, o aparelho não tem a fila nem a resposta guardada. Pode ser só o teste (esperar a lista guardada antes de desligar a rede) ou uma falha real: o app sem a lista guardada não mostra o que acabou de subir.

## Checklist

- [ ] Reproduzir (`npx playwright test e2e/sem-internet.spec.ts --repeat-each=5`, ou a suíte inteira) e confirmar a causa
- [ ] Se for só o teste, torná-lo determinístico; se for do app, corrigir com teste
- [ ] Verificações do projeto rodando e PR aberto para `main`
