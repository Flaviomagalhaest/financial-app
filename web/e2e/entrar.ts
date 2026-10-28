import type { Page } from "@playwright/test";

/** Entra pelo formulário; o Cognito falso aceita qualquer senha dos usuários de teste. */
export async function entrar(page: Page, email = "flavio@teste.com") {
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha").fill("uma senha qualquer");
  await page.getByRole("button", { name: "Entrar" }).click();
}
