import { expect, type Page, test } from "@playwright/test";
import { entrar } from "./entrar";
import { cadastrar, digitar } from "./lancar";

// A edição chega ao servidor (versão 2), mas a resposta se perde, e a edição fica na fila sobre a
// versão 1 (ticket 169). Depois disso a rede fica fora até `voltar()`.
async function editarPerdendoAResposta(page: Page) {
  const s = String(Date.now());
  const [conta, mercado] = [`Corrente ${s}`, `Mercado ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", mercado, "despesa");

  await page.goto("/#/novo");
  const salvar = page.getByRole("button", { name: "Salvar" });
  await digitar(page, "1", "00");
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: mercado }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(`Jantar ${s}`);
  await page.getByRole("button", { name: "Pronto" }).click();
  await salvar.click();
  const linha = page.getByRole("listitem").filter({ hasText: `Jantar ${s}` });
  await expect(linha).toContainText("− R$ 1,00");
  await expect(linha).not.toContainText("não enviado");

  let chegou = false;
  let foraDoAr = true;
  await page.route("**/api/lancamentos/lote", async (rota) => {
    if (!foraDoAr) return rota.continue();
    if (!chegou) {
      chegou = true;
      await rota.fetch();
    }
    await rota.abort("connectionreset");
  });
  await linha.getByRole("link", { name: `Editar Jantar ${s}` }).click();
  await digitar(page, "2");
  await expect(page.getByTestId("valor")).toHaveText("R$ 10,02");
  await salvar.click();
  await expect(linha).toContainText("− R$ 10,02");
  await expect.poll(() => chegou).toBe(true);
  await expect(linha).toContainText("não enviado");
  return { linha, nome: `Jantar ${s}`, voltar: () => void (foraDoAr = false) };
}

async function excluir(page: Page, nome: string) {
  page.once("dialog", (dialogo) => void dialogo.accept());
  await page.getByRole("button", { name: `Excluir ${nome}` }).click();
}

test("edição com a resposta perdida sobe ao reabrir, sem a pessoa mexer de novo", async ({ page }) => {
  const { linha, nome, voltar } = await editarPerdendoAResposta(page);
  await page.reload({ waitUntil: "commit" });
  voltar();
  await expect(linha).toContainText("− R$ 10,02");
  await expect(linha).not.toContainText("não enviado", { timeout: 3_000 });

  await excluir(page, nome);
  await expect(linha).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect(linha).toHaveCount(0);
});

test("a exclusão que entra no lugar da edição com a resposta perdida sai sem conflito", async ({ page }) => {
  const { linha, nome, voltar } = await editarPerdendoAResposta(page);
  // Reabre ainda sem rede e exclui antes de a edição subir: a exclusão entra no lugar dela.
  await page.reload();
  await expect(linha).toContainText("− R$ 10,02");
  await excluir(page, nome);
  await expect(linha).toHaveCount(0);
  voltar();
  // Com a rede de volta, a exclusão sobe sozinha e a linha não reaparece como conflito.
  const aceita = page.waitForResponse(
    async (r) => r.url().endsWith("/api/lancamentos/lote") && /"excluir"/.test(r.request().postData() ?? "") && /"aceita"/.test(await r.text()),
    { timeout: 20_000 },
  );
  await page.reload();
  await aceita;
  await page.reload();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect(page.getByText("conflito")).toHaveCount(0);
  await expect(linha).toHaveCount(0);
});
