import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";

test.use({ timezoneId: "America/Sao_Paulo", viewport: { width: 360, height: 740 } });

// Cada tela com o que só aparece depois de carregada: medir antes disso esconde o estouro.
const TELAS: [string, string][] = [
  ["hoje", "Hoje"],
  ["mes", "Adicionar item"],
  ["cartoes", "Cartões"],
  ["historico", "Histórico"],
  ["futuro", "Futuro"],
  ["modelo-do-planejamento", "Salvar modelo padrão"],
  ["busca", "Salvar esta busca"],
];

/** A página não pode ficar mais larga que a tela, senão o celular desloca a área visível e a barra de baixo sai cortada. */
async function larguraDaPagina(page: Page) {
  return page.evaluate(() => ({ pagina: document.documentElement.scrollWidth, tela: window.innerWidth }));
}

for (const fonte of [100, 130]) {
  test(`nenhuma tela passa da largura do celular (360 px, fonte ${fonte}%)`, async ({ page }) => {
    const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
    await page.goto("/#/hoje");
    await entrar(page);
    const api = await apiDaPagina(page);
    // Uma categoria de nome comprido: sem ela o select do novo item fica estreito e esconde o estouro.
    await api.criar("/api/categorias", { nome: `Categoria com um nome bem comprido ${s}`, tipo: "despesa" });
    await page.addStyleTag({ content: `html { font-size: ${fonte}% }` });

    for (const [tela, carregada] of TELAS) {
      await page.goto(`/#/${tela}`);
      await expect(page.getByText(carregada, { exact: true }).first()).toBeVisible();
      await page.waitForLoadState("networkidle");
      // A fileira de salvar a busca só existe com o formulário aberto.
      if (tela === "busca") await page.getByRole("button", { name: "Salvar esta busca" }).click();
      const { pagina, tela: largura } = await larguraDaPagina(page);
      expect(pagina, `tela ${tela}`).toBeLessThanOrEqual(largura);
    }
  });
}
