import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";

const CARTOES = ["Histórico", "Futuro", "Busca", "Favoritos", "Contas e categorias", "Configurações"];

async function abrirNoCelular(page: Page) {
  await page.setViewportSize({ width: 390, height: 800 });
  await page.goto("/");
  await entrar(page);
  return page.getByRole("navigation", { name: "Telas" });
}

test("no celular a barra de baixo tem cinco itens só com ícone, achados pelo nome acessível", async ({ page }) => {
  const barra = await abrirNoCelular(page);
  for (const nome of ["Hoje", "Mês", "Novo lançamento", "Cartões", "Explorar"]) {
    await expect(barra.getByRole("link", { name: nome, exact: true })).toBeVisible();
  }
  await expect(barra.getByRole("link")).toHaveCount(5);
  await expect(barra.getByRole("link", { name: "Histórico" })).toHaveCount(0);
  // Nenhum nome aparece escrito na barra: o texto fica só para o leitor de tela (1 px).
  expect((await barra.getByText("Hoje").boundingBox())!.width).toBeLessThanOrEqual(1);
});

test("a tela Explorar traz seis cartões em duas colunas e abre Histórico e Futuro", async ({ page }) => {
  const barra = await abrirNoCelular(page);
  await barra.getByRole("link", { name: "Explorar" }).click();
  await expect(page.getByRole("heading", { name: "Explorar", level: 2 })).toBeVisible();
  await expect(barra.getByRole("link", { name: "Explorar" })).toHaveAttribute("aria-current", "page");

  const principal = page.getByRole("main");
  const links = principal.getByRole("link");
  await expect(links).toHaveText(CARTOES);
  const a = (await links.nth(0).boundingBox())!;
  const b = (await links.nth(1).boundingBox())!;
  const c = (await links.nth(2).boundingBox())!;
  expect(Math.abs(a.y - b.y)).toBeLessThan(2);
  expect(c.y).toBeGreaterThan(a.y + a.height - 1);

  await links.nth(0).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect(barra.getByRole("link", { name: "Explorar" })).toHaveAttribute("aria-current", "page");
  await barra.getByRole("link", { name: "Explorar" }).click();
  await principal.getByRole("link", { name: "Futuro" }).click();
  await expect(page.getByRole("heading", { name: "Futuro", level: 2 })).toBeVisible();
  await expect(barra.getByRole("link", { name: "Explorar" })).toHaveAttribute("aria-current", "page");
});

test("no celular, a grade marca toda tela fora de Hoje, Mês, Cartões e lançar", async ({ page }) => {
  const barra = await abrirNoCelular(page);
  const marcado = barra.locator('[aria-current="page"]');
  for (const rota of ["busca", "favoritos", "contas-e-categorias", "configuracoes", "edicoes-em-lote", "historico", "futuro", "explorar"]) {
    await page.goto(`/#/${rota}`);
    await expect(marcado).toHaveAttribute("aria-label", "Explorar");
  }
  // A pílula atrás do ícone marcado muda o fundo do ícone, que nos outros fica transparente.
  const fundo = (nome: string) => barra.getByRole("link", { name: nome, exact: true }).locator("svg").evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(await fundo("Explorar")).not.toBe("rgba(0, 0, 0, 0)");
  expect(await fundo("Hoje")).toBe("rgba(0, 0, 0, 0)");
  await page.goto("/#/modelo-do-planejamento");
  await expect(marcado).toHaveAttribute("aria-label", "Mês");
  await page.goto("/#/novo");
  await expect(marcado).toHaveCount(0);
  await page.goto("/#/cartoes");
  await expect(marcado).toHaveAttribute("aria-label", "Cartões");
});

test("na tela larga a barra lateral segue com os nomes e sem Explorar", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  await entrar(page);
  const barra = page.getByRole("navigation", { name: "Telas" });
  await expect(barra.getByRole("link")).toHaveText(["Novo lançamento", "Hoje", "Mês", "Cartões", "Histórico", "Futuro"]);
  await expect(barra.getByRole("link", { name: "Explorar" })).toHaveCount(0);

  await page.goto("/#/explorar");
  await expect(page.getByRole("heading", { name: "Explorar", level: 2 })).toBeVisible();
  await expect(barra.locator('[aria-current="page"]')).toHaveCount(0);
  await page.goto("/#/busca");
  await expect(barra.getByRole("link", { name: "Histórico" })).toHaveAttribute("aria-current", "page");
  await page.goto("/#/modelo-do-planejamento");
  await expect(barra.getByRole("link", { name: "Mês" })).toHaveAttribute("aria-current", "page");
});
