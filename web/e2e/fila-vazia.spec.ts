import { expect, test } from "@playwright/test";
import { entrar } from "./entrar";
import { esperarFilaVazia } from "./fila";
import { cadastrar, lancar } from "./lancar";

// Ticket 182: com a CPU ocupada, a conferência pelo aviso passa com o pedido ainda na fila, porque
// o aviso só aparece depois de a tela ler a fila. A conferência comum espera a fila de verdade.
test("com a CPU estrangulada, a conferência da fila vazia não passa com um pedido na fila", async ({ page, context }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, mercado] = [`Corrente ${s}`, `Mercado ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  await context.setOffline(true);
  await lancar(page, { teclas: ["4", "5", "00"], conta, categoria: mercado, descricao: `Padaria ${s}` });

  const cdp = await context.newCDPSession(page);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 30 });
  await page.goto("/#/");
  await page.reload();
  const aviso = page.getByTestId("nao-enviados");

  // O que valia antes: o aviso ainda não existe e a fila cheia passa por vazia.
  await expect(aviso).toHaveCount(0, { timeout: 500 });
  // A conferência comum espera: com a fila cheia, ela não passa.
  await expect(esperarFilaVazia(page, { timeout: 2_000 })).rejects.toThrow();

  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 1 });
  await context.setOffline(false);
  await expect(aviso).toBeVisible();
  await page.getByRole("button", { name: "Enviar agora" }).click();
  await esperarFilaVazia(page);
});
