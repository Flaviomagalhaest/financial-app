import { expect, test } from "@playwright/test";
import { entrar } from "./entrar";

test("mostra que a API está no ar e avisa quando a rede cai", async ({ page, context }) => {
  await page.goto("/");
  await entrar(page);
  await expect(page.getByTestId("estado-da-api")).toHaveText("API no ar");

  await context.setOffline(true);
  await page.getByRole("button", { name: "Verificar de novo" }).click();
  await expect(page.getByTestId("estado-da-api")).toHaveText("Sem conexão");

  await context.setOffline(false);
  await page.getByRole("button", { name: "Verificar de novo" }).click();
  await expect(page.getByTestId("estado-da-api")).toHaveText("API no ar");
});

test("separa sessão vencida e API fora do ar, e cada estado se desfaz sozinho", async ({ page }) => {
  await page.goto("/");
  await entrar(page);
  const estado = page.getByTestId("estado-da-api");
  await expect(estado).toHaveText("API no ar");

  let status = 401;
  await page.route("**/api/eu", (rota) => rota.fulfill({ status, body: "{}", contentType: "application/json" }));

  await page.getByRole("button", { name: "Verificar de novo" }).click();
  await expect(estado).toHaveText("Sessão vencida");
  await expect(page.getByRole("button", { name: "Entrar de novo" })).toBeVisible();

  status = 429;
  await page.getByRole("button", { name: "Verificar de novo" }).click();
  await expect(estado).toHaveText("API ocupada ou fora do ar");
  await expect(page.getByRole("button", { name: "Entrar de novo" })).toHaveCount(0);

  status = 503;
  await page.getByRole("button", { name: "Verificar de novo" }).click();
  await expect(estado).toHaveText("API ocupada ou fora do ar");

  // A falha passou: voltar à aba verifica sozinho, sem o botão.
  await page.unroute("**/api/eu");
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(estado).toHaveText("API no ar");
});

test("verifica de novo sozinho quando a rede volta", async ({ page, context }) => {
  await page.goto("/");
  await entrar(page);
  const estado = page.getByTestId("estado-da-api");
  await expect(estado).toHaveText("API no ar");

  await context.setOffline(true);
  await page.getByRole("button", { name: "Verificar de novo" }).click();
  await expect(estado).toHaveText("Sem conexão");

  await context.setOffline(false);
  await expect(estado).toHaveText("API no ar");
});
