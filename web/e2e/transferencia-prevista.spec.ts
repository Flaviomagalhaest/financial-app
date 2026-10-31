import { expect, test, type Page } from "@playwright/test";
import { cadastrar, digitar } from "./lancar";
import { entrar } from "./entrar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

/** Dia `deslocamento` dias a partir de hoje em São Paulo, como `AAAA-MM-DD`. */
function dia(deslocamento: number): string {
  const data = new Date(Date.now() + deslocamento * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(data);
}

async function transferir(page: Page, { de, para, teclas, descricao, data, situacao }: { de: string; para: string; teclas: string[]; descricao: string; data: string; situacao?: "Previsto" }) {
  await page.goto("/#/novo");
  await page.getByRole("button", { name: "Transferência", exact: true }).click();
  await digitar(page, ...teclas);
  await page.getByRole("group", { name: "De" }).getByRole("button", { name: de }).click();
  await page.getByRole("group", { name: "Para" }).getByRole("button", { name: para }).click();
  await page.getByLabel("Descrição").fill(descricao);
  await page.getByLabel("Data").fill(data);
  if (situacao) await page.getByRole("group", { name: "Situação" }).getByRole("button", { name: situacao, exact: true }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Hoje", level: 2 })).toBeVisible();
}

test("transferência prevista atrasada aparece nas contas da semana e se confirma ajustando", async ({ page }) => {
  const s = String(Date.now());
  const [corrente, poupanca] = [`Corrente ${s}`, `Poupança ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", corrente, "corrente");
  await cadastrar(page, "Nova conta", poupanca, "poupanca");

  // Data passada, mas prevista à mão: a troca Realizado/Previsto da tela de transferência.
  await transferir(page, { de: corrente, para: poupanca, teclas: ["5", "0", "00"], descricao: `Reserva ${s}`, data: dia(-1), situacao: "Previsto" });

  const bloco = page.getByRole("region", { name: "Contas da semana" });
  const minha = bloco.getByRole("listitem").filter({ hasText: `Reserva ${s}` });
  await expect(minha).toContainText("atrasado");
  await expect(minha).toContainText("R$ 50,00");
  await expect(page.getByTestId("atrasados")).toBeVisible();

  // Previsto não mexe no saldo.
  await page.goto("/#/contas-e-categorias");
  await expect(page.getByRole("listitem").filter({ hasText: corrente })).toContainText("R$ 0,00");

  // Ajustar: saiu menos e caiu hoje.
  await page.goto("/#/hoje");
  await bloco.getByRole("button", { name: `Ajustar Reserva ${s}` }).click();
  const ajuste = bloco.getByRole("group", { name: `Ajuste de Reserva ${s}` });
  await digitar(page, "Apagar", "Apagar", "Apagar", "Apagar", "4", "0", "00");
  await expect(ajuste.getByTestId("valor")).toHaveText("R$ 40,00");
  await ajuste.getByLabel("Data").fill(dia(0));
  await ajuste.getByRole("button", { name: "Confirmar com ajuste" }).click();
  await expect(minha).toHaveCount(0);

  // Realizada: o saldo das duas contas anda pelo valor confirmado.
  await page.goto("/#/contas-e-categorias");
  await expect(page.getByRole("listitem").filter({ hasText: corrente })).toContainText("R$ 40,00");
  await expect(page.getByRole("listitem").filter({ hasText: poupanca })).toContainText("R$ 40,00");
});
