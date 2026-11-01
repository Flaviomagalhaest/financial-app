import { expect, test } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { cadastrar, lancar } from "./lancar";

// Sem service worker: o `page.route` não pega o que sobe por ele.
test.use({ serviceWorkers: "block" });

test("editar: o que se digita antes de o lançamento carregar não se perde", async ({ page }) => {
  const s = String(Date.now());
  const [conta, mercado] = [`Corrente ${s}`, `Mercado ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  await lancar(page, { teclas: ["1", "0", "0", "0", "0"], conta, categoria: mercado, descricao: `Feira ${s}` });
  const editar = page.getByRole("link", { name: `Editar Feira ${s}` });
  await expect(editar).toBeVisible();
  // Apagar o banco do aparelho perderia o que ainda está na fila: espera o servidor ter o lançamento.
  const api = await apiDaPagina(page);
  await expect.poll(async () => (await api.ler("/api/lancamentos")).some((l: { descricao: string }) => l.descricao === `Feira ${s}`)).toBe(true);
  const href = await editar.getAttribute("href");

  // Segura a lista de lançamentos: a tela abre a edição sem o lançamento no aparelho.
  let soltar!: () => void;
  const segurada = new Promise<void>((r) => (soltar = r));
  await page.route("**/api/lancamentos", async (rota) => {
    if (rota.request().method() === "GET") await segurada;
    await rota.continue();
  });
  // Só o banco de dados: o do login fica, ou a tela volta para o "Entrar".
  await page.goto("about:blank");
  await page.goto("/");
  await page.evaluate(() => new Promise((ok) => Object.assign(indexedDB.deleteDatabase("financial-app-dados"), { onsuccess: ok, onerror: ok, onblocked: ok })));
  await page.goto(`/${href}`);
  await expect(page.getByRole("heading", { name: "Editar lançamento", level: 2 })).toBeVisible();

  // Antes de carregar, o formulário não aceita o que apagaria: "Detalhes" está desativado.
  await expect(page.getByRole("button", { name: /^Detalhes/ })).toBeDisabled();
  soltar();
  await expect(page.getByTestId("valor")).toHaveText("R$ 100,00");
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await expect(page.getByLabel("Descrição")).toHaveValue(`Feira ${s}`);
});
