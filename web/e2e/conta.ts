import type { Locator, Page } from "@playwright/test";

/** Abre o menu da conta (o círculo com a inicial, no topo) e toca no item: Configurações, Contas e categorias, Favoritos ou Sair. */
export async function peloMenuDaConta(page: Page, item: "Configurações" | "Contas e categorias" | "Favoritos" | "Sair") {
  await page.getByLabel(/^Conta de /).click();
  const menu = page.getByRole("group", { name: "Menu da conta" });
  await (item === "Sair" ? menu.getByRole("button", { name: "Sair" }) : menu.getByRole("link", { name: item })).click();
}

/**
 * Abre o ⋯ da linha de `titulo` e toca na ação de nome acessível `nome` (botão, ou o papel dado):
 * `pelaLinha(page, "Mercado", "Excluir Mercado")`. `linha` limita a busca à linha, quando há títulos repetidos.
 */
export async function pelaLinha(linha: Locator | Page, titulo: string, nome: string | RegExp, papel: "button" | "link" = "button") {
  await linha.getByLabel(`Mais ações ${titulo}`).click();
  await linha.getByRole(papel, { name: nome }).click();
}
