import { expect, test, type Page } from "@playwright/test";
import { desconectar, renovacoes } from "./cognito-falso";
import { entrar } from "./entrar";

const verificar = (page: Page) => page.getByRole("button", { name: "Verificar de novo" }).click();

test("entra com e-mail e senha no próprio app e continua logado ao abrir de novo", async ({ page }) => {
  await page.goto("/");
  await entrar(page, "flavio@teste.com");

  await expect(page.getByText("Entrou como flavio@teste.com")).toBeVisible();
  await expect(page.getByTestId("estado-da-api")).toHaveText("API no ar");

  await page.reload();
  await expect(page.getByText("Entrou como flavio@teste.com")).toBeVisible();
  await expect(page.getByLabel("Senha")).toHaveCount(0);
});

test("e-mail ou senha errados não entram e dizem por quê", async ({ page }) => {
  await page.goto("/");
  await entrar(page, "intruso@teste.com");

  await expect(page.getByRole("alert")).toHaveText("E-mail ou senha incorretos.");
  await expect(page.getByLabel("Senha")).toBeVisible();
});

test("sem internet e com o acesso vencido o app segue logado e renova quando a rede volta", async ({
  page,
  context,
}) => {
  await page.clock.install();
  await page.goto("/");
  await entrar(page, "esposa@teste.com");
  await expect(page.getByTestId("estado-da-api")).toHaveText("API no ar");
  const antes = await renovacoes();

  await context.setOffline(true);
  await page.clock.fastForward("16:00");
  await verificar(page);
  await expect(page.getByTestId("estado-da-api")).toHaveText("Sem conexão");
  await expect(page.getByText("Entrou como esposa@teste.com")).toBeVisible();

  await context.setOffline(false);
  await verificar(page);
  await expect(page.getByTestId("estado-da-api")).toHaveText("API no ar");
  expect(await renovacoes()).toBe(antes + 1);
});

test("sessões desconectadas pelo dono pedem o login de novo", async ({ page }) => {
  await page.clock.install();
  await page.goto("/");
  await entrar(page, "esposa@teste.com");
  await expect(page.getByTestId("estado-da-api")).toHaveText("API no ar");

  await desconectar("esposa@teste.com");
  await page.clock.fastForward("16:00");
  await verificar(page);

  await expect(page.getByText("Sua sessão foi encerrada. Entre de novo.")).toBeVisible();
  await expect(page.getByLabel("Senha")).toBeVisible();
});

test("sair volta ao formulário e não deixa a sessão no aparelho", async ({ page }) => {
  await page.goto("/");
  await entrar(page, "flavio@teste.com");
  await expect(page.getByText("Entrou como flavio@teste.com")).toBeVisible();

  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page.getByLabel("Senha")).toBeVisible();

  await page.reload();
  await expect(page.getByLabel("Senha")).toBeVisible();
});

test("a API recusa quem não entrou", async ({ request }) => {
  const resposta = await request.get("/api/eu");

  expect(resposta.status()).toBe(401);
});
