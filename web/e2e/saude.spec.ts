import { expect, test } from "@playwright/test";

test("mostra que a API está no ar e avisa quando a rede cai", async ({ page, context }) => {
  await page.goto("/");
  await expect(page.getByTestId("estado-da-api")).toHaveText("API no ar");

  await context.setOffline(true);
  await page.getByRole("button", { name: "Verificar de novo" }).click();
  await expect(page.getByTestId("estado-da-api")).toHaveText("Sem conexão");

  await context.setOffline(false);
  await page.getByRole("button", { name: "Verificar de novo" }).click();
  await expect(page.getByTestId("estado-da-api")).toHaveText("API no ar");
});
