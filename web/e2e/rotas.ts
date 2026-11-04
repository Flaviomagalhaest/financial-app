import type { Page } from "@playwright/test";

/**
 * Espera as rotas em andamento terminarem e as solta. Sem isso, uma leitura que ainda está no
 * `rota.fetch()` quando o teste acaba perde a resposta no fechamento do contexto
 * ("Response has been disposed") — a tela e o service worker leem a mesma lista (ticket 183).
 * Usar em `test.afterEach`.
 */
export async function soltarRotas(page: Page) {
  // `page.route` e `context.route` são listas separadas: cada uma tem o seu `unrouteAll`.
  await page.unrouteAll({ behavior: "wait" });
  await page.context().unrouteAll({ behavior: "wait" });
}
