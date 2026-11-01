import { expect, type Page } from "@playwright/test";

/** Algumas telas de cadastro ainda não existem: o teste prepara os dados pela API, com o token da página. */
export async function tokenDaPagina(page: Page): Promise<string> {
  // Recarregar no meio do login volta ao formulário, e nenhum pedido leva o token.
  await expect(page.getByRole("button", { name: "Sair" })).toBeVisible();
  const pedido = page.waitForRequest((r) => r.url().includes("/api/") && !!r.headers().authorization);
  await page.reload();
  return (await pedido).headers().authorization;
}

/** `criar(caminho, corpo)` faz o POST com o token da página e exige sucesso; `mudar`, o PATCH; `substituir`, o PUT; `ler(caminho)`, o GET. */
export async function apiDaPagina(page: Page) {
  const headers = { authorization: await tokenDaPagina(page) };
  return {
    async criar(caminho: string, data: object) {
      const resposta = await page.request.post(caminho, { headers, data });
      expect(resposta.ok(), await resposta.text()).toBe(true);
      return resposta.json();
    },
    async mudar(caminho: string, data: object) {
      const resposta = await page.request.patch(caminho, { headers, data });
      expect(resposta.ok(), await resposta.text()).toBe(true);
      return resposta.json();
    },
    async substituir(caminho: string, data: object) {
      const resposta = await page.request.put(caminho, { headers, data });
      expect(resposta.ok(), await resposta.text()).toBe(true);
      return resposta.json();
    },
    async ler(caminho: string) {
      const resposta = await page.request.get(caminho, { headers });
      expect(resposta.ok(), await resposta.text()).toBe(true);
      return resposta.json();
    },
  };
}
