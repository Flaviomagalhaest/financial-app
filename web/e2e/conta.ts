import type { Page } from "@playwright/test";

/** Abre o menu da conta (o círculo com a inicial, no topo) e toca no item: Configurações, Contas e categorias, Favoritos ou Sair. */
export async function peloMenuDaConta(page: Page, item: "Configurações" | "Contas e categorias" | "Favoritos" | "Sair") {
  await page.getByLabel(/^Conta de /).click();
  const menu = page.locator(".menu-da-conta");
  await (item === "Sair" ? menu.getByRole("button", { name: "Sair" }) : menu.getByRole("link", { name: item })).click();
}
