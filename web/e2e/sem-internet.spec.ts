import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";
import { cadastrar, lancar } from "./lancar";

/** Entra, cadastra uma conta e uma categoria de despesa e deixa as duas guardadas no aparelho. */
async function prepararCasal(page: Page, email?: string) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, mercado] = [`Corrente ${s}`, `Mercado ${s}`];
  await page.goto("/#/cadastro");
  await entrar(page, email);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  return { s, conta, mercado };
}

const aba = (page: Page, nome: string) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome }).click();

test("lança sem internet, mostra ⏳ e a contagem na Hoje e envia uma vez só quando a rede volta", async ({ page, context }) => {
  const { s, conta, mercado } = await prepararCasal(page);

  await context.setOffline(true);
  await lancar(page, { teclas: ["4", "5", "00"], conta, categoria: mercado, descricao: `Padaria ${s}` });

  const linha = page.getByRole("listitem").filter({ hasText: `Padaria ${s}` });
  await expect(linha).toContainText("− R$ 45,00");
  await expect(linha).toContainText("⏳ não enviado");
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("1 lançamento não enviado");

  await context.setOffline(false);
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  await aba(page, "Histórico");
  await expect(linha).not.toContainText("não enviado");
  await page.reload();
  await expect(linha).toHaveCount(1);
  await expect(linha).toContainText("− R$ 45,00");
});

test("edita e exclui sem internet e, se a resposta do envio se perde, reenviar não duplica", async ({ page, context }) => {
  const { s, conta, mercado } = await prepararCasal(page);
  await lancar(page, { teclas: ["1", "00"], conta, categoria: mercado, descricao: `Feira ${s}` });
  await lancar(page, { teclas: ["2", "00"], conta, categoria: mercado, descricao: `Farmácia ${s}` });
  const feira = page.getByRole("listitem").filter({ hasText: `Feira ${s}` });
  const farmacia = page.getByRole("listitem").filter({ hasText: `Farmácia ${s}` });
  await expect(feira).not.toContainText("não enviado");
  await expect(farmacia).not.toContainText("não enviado");

  await context.setOffline(true);
  await feira.getByRole("link", { name: `Editar Feira ${s}` }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 1,00");
  await page.getByRole("button", { name: "7", exact: true }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(feira).toContainText("− R$ 10,07");
  await expect(feira).toContainText("⏳ não enviado");
  page.once("dialog", (dialogo) => void dialogo.accept());
  await farmacia.getByRole("button", { name: `Excluir Farmácia ${s}` }).click();
  await expect(farmacia).toHaveCount(0);
  await lancar(page, { teclas: ["3", "00"], conta, categoria: mercado, descricao: `Açougue ${s}` });
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("3 lançamentos não enviados");

  // O servidor grava o lote, mas a resposta não chega ao aparelho.
  let perdidas = 0;
  await page.route("**/api/lancamentos/lote", async (rota) => {
    if (perdidas > 0) return rota.continue();
    perdidas++;
    await rota.fetch();
    await rota.abort("connectionreset");
  });
  await context.setOffline(false);
  await expect.poll(() => perdidas).toBe(1);
  await expect(page.getByTestId("nao-enviados")).toContainText("3 lançamentos não enviados");

  await page.getByRole("button", { name: "Enviar agora" }).click();
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  await page.reload();
  await aba(page, "Histórico");
  await expect(feira).toHaveCount(1);
  await expect(feira).toContainText("− R$ 10,07");
  await expect(farmacia).toHaveCount(0);
  await expect(page.getByRole("listitem").filter({ hasText: `Açougue ${s}` })).toHaveCount(1);
});

test("recusado pelo servidor fica 'não enviado: <motivo>' para corrigir ou descartar, e o resto da fila sobe", async ({ page, context }) => {
  // O aparelho guardou uma conta que o servidor não tem mais (como um cartão arquivado depois).
  const sumida = `Conta sumida ${Date.now()}`;
  await page.route("**/api/contas", async (rota) => {
    if (rota.request().method() !== "GET") return rota.continue();
    const resposta = await rota.fetch();
    const contas = await resposta.json();
    await rota.fulfill({ response: resposta, json: [...contas, { id: crypto.randomUUID(), nome: sumida, tipo: "corrente" }] });
  });
  const { s, conta, mercado } = await prepararCasal(page);

  await context.setOffline(true);
  await lancar(page, { teclas: ["1", "1"], conta: sumida, categoria: mercado, descricao: `Corrigir ${s}` });
  await lancar(page, { teclas: ["2", "2"], conta, categoria: mercado, descricao: `Bom ${s}` });
  await lancar(page, { teclas: ["3", "3"], conta: sumida, categoria: mercado, descricao: `Descartar ${s}` });
  await context.setOffline(false);

  const corrigir = page.getByRole("listitem").filter({ hasText: `Corrigir ${s}` });
  const bom = page.getByRole("listitem").filter({ hasText: `Bom ${s}` });
  const descartar = page.getByRole("listitem").filter({ hasText: `Descartar ${s}` });
  await expect(corrigir).toContainText("não enviado: conta não encontrada");
  await expect(descartar).toContainText("não enviado: conta não encontrada");
  await expect(bom).not.toContainText("não enviado");
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("2 lançamentos não enviados (2 recusados");

  await aba(page, "Histórico");
  await descartar.getByRole("button", { name: `Descartar Descartar ${s}` }).click();
  await expect(descartar).toHaveCount(0);
  await corrigir.getByRole("link", { name: `Corrigir Corrigir ${s}` }).click();
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(corrigir).toContainText(conta);
  await expect(corrigir).not.toContainText("não enviado");

  await page.reload();
  await expect(corrigir).toHaveCount(1);
  await expect(bom).toHaveCount(1);
  await expect(descartar).toHaveCount(0);
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
});
