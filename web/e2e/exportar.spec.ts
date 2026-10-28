import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";

/** A API de verdade não tem o bucket de exportações aqui: a resposta e o arquivo são de mentira,
 *  e a URL é de outra origem, como a assinada do S3 (o service worker não a toca). */
async function simularExportacao(page: Page, arquivo: string) {
  const pedidos: unknown[] = [];
  await page.route("**/api/exportacoes", async (rota) => {
    pedidos.push(rota.request().postDataJSON());
    await rota.fulfill({
      json: { url: `https://exportacoes.exemplo.test/${arquivo}`, arquivo, expira_em: "2026-10-28T12:05:00-03:00" },
    });
  });
  await page.route("https://exportacoes.exemplo.test/*", (rota) =>
    rota.fulfill({
      body: "conteudo",
      headers: { "Content-Disposition": `attachment; filename="${arquivo}"` },
    }),
  );
  return pedidos;
}

test("as configurações baixam o backup e o CSV de planilha", async ({ page }) => {
  const pedidos = await simularExportacao(page, "financial-app-backup-2026-10-28.zip");
  await page.goto("/");
  await entrar(page);

  await page.getByRole("link", { name: "Configurações" }).click();
  await expect(page.getByRole("heading", { name: "Configurações", level: 2 })).toBeVisible();

  const backup = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar tudo (backup .zip)" }).click();
  expect((await backup).suggestedFilename()).toBe("financial-app-backup-2026-10-28.zip");

  const planilha = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar lançamentos (planilha .csv)" }).click();
  await planilha;

  expect(pedidos).toEqual([{ formato: "backup" }, { formato: "planilha" }]);
});

test("sem internet o botão de exportar fica desligado e avisa", async ({ page, context }) => {
  await page.goto("/");
  await entrar(page);
  await page.getByRole("link", { name: "Configurações" }).click();
  const botao = page.getByRole("button", { name: "Exportar tudo (backup .zip)" });
  await expect(botao).toBeEnabled();

  await context.setOffline(true);

  await expect(botao).toBeDisabled();
  await expect(page.getByText("Exportar precisa de internet.")).toBeVisible();

  await context.setOffline(false);
  await expect(botao).toBeEnabled();
});

test("se a API falhar, a tela mostra o erro e deixa tentar de novo", async ({ page }) => {
  await page.route("**/api/exportacoes", (rota) => rota.fulfill({ status: 500, body: "erro" }));
  await page.goto("/");
  await entrar(page);
  await page.getByRole("link", { name: "Configurações" }).click();

  await page.getByRole("button", { name: "Exportar tudo (backup .zip)" }).click();

  await expect(page.getByRole("alert")).toHaveText("Não foi possível exportar. Tente de novo.");
  await expect(page.getByRole("button", { name: "Exportar tudo (backup .zip)" })).toBeEnabled();
});
