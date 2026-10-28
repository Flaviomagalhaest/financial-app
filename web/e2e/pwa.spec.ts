import { expect, test } from "@playwright/test";
import { entrar } from "./entrar";

const ABAS = ["Hoje", "Mês", "Cartões", "Histórico", "Futuro"];

test("o manifesto deixa o app instalável e traz o atalho Novo lançamento", async ({ page, request }) => {
  await page.goto("/");
  const href = await page.locator('link[rel="manifest"]').getAttribute("href");
  const resposta = await request.get(href!);
  expect(resposta.ok()).toBe(true);
  const manifesto = await resposta.json();

  expect(manifesto.display).toBe("standalone");
  expect(manifesto.name).toBe("Financial App");
  expect(manifesto.shortcuts).toEqual([expect.objectContaining({ name: "Novo lançamento", url: "/#/novo" })]);
  const tamanhos = manifesto.icons.map((icone: { sizes: string }) => icone.sizes);
  expect(tamanhos).toEqual(expect.arrayContaining(["192x192", "512x512"]));
  for (const icone of manifesto.icons) {
    expect((await request.get(icone.src)).ok()).toBe(true);
  }
});

test("a casca abre sem internet depois de instalada", async ({ page, context }) => {
  await page.goto("/");
  await entrar(page);
  await expect(page.getByText("Entrou como flavio@teste.com")).toBeVisible();
  await page.evaluate(() => navigator.serviceWorker.ready);
  // O service worker só passa a controlar a página na próxima abertura.
  await page.reload();
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);

  await context.setOffline(true);
  await page.reload();

  await expect(page.getByRole("heading", { name: "Financial App" })).toBeVisible();
  const abas = page.getByRole("navigation", { name: "Telas" });
  for (const nome of ABAS) await expect(abas.getByRole("link", { name: nome })).toBeVisible();
  await expect(page.getByTestId("estado-da-api")).toHaveText("Sem conexão");
});

test("navega entre as abas vazias e abre o novo lançamento pelo botão e pelo atalho", async ({ page }) => {
  await page.goto("/");
  await entrar(page);
  const abas = page.getByRole("navigation", { name: "Telas" });

  for (const nome of ABAS.slice(1)) {
    await abas.getByRole("link", { name: nome }).click();
    await expect(page.getByRole("heading", { name: nome, level: 2 })).toBeVisible();
    await expect(abas.getByRole("link", { name: nome })).toHaveAttribute("aria-current", "page");
  }

  await abas.getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await expect(page.getByRole("heading", { name: "Novo lançamento", level: 2 })).toBeVisible();

  await page.goto("/#/hoje");
  await page.goto("/#/novo");
  await expect(page.getByRole("heading", { name: "Novo lançamento", level: 2 })).toBeVisible();
});

test("celular tem as abas embaixo e tela larga tem as abas ao lado", async ({ page }) => {
  await page.goto("/");
  await entrar(page);
  const abas = page.getByRole("navigation", { name: "Telas" });
  const conteudo = page.getByRole("main");

  await page.setViewportSize({ width: 390, height: 800 });
  const celular = (await abas.boundingBox())!;
  expect(celular.y + celular.height).toBeCloseTo(800, 0);
  expect(celular.width).toBeCloseTo(390, 0);

  await page.setViewportSize({ width: 1280, height: 800 });
  const larga = (await abas.boundingBox())!;
  const principal = (await conteudo.boundingBox())!;
  expect(larga.x).toBe(0);
  expect(larga.width).toBeLessThan(300);
  expect(principal.x).toBeGreaterThanOrEqual(larga.x + larga.width);
});
