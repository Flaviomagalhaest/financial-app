import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { lancar } from "./lancar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

function dia(deslocamento: number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(Date.now() + deslocamento * 86_400_000));
}

/**
 * O aparelho guarda só a janela (ticket 166, ADR 0024): a lista guardada não tem esses lançamentos,
 * e as telas da fatura, do Mês e do parcelamento precisam achá-los no servidor.
 */
async function aparelhoSemALista(page: Page) {
  await page.route((url) => url.pathname === "/api/lancamentos", (rota) => (rota.request().method() === "GET" ? rota.fulfill({ json: [] }) : rota.fallback()));
}

/** Um cartão, uma categoria, uma compra à vista hoje e uma compra parcelada em 3 no cartão. */
async function prepararCartao(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/cartoes");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Cartões", level: 2 })).toBeVisible();
  const api = await apiDaPagina(page);
  const cartao = await api.criar("/api/cartoes", { nome: `Visa ${s}`, dia_fechamento: 10, dia_vencimento: 20 });
  const categoria = await api.criar("/api/categorias", { nome: `Mercado ${s}`, tipo: "despesa" });
  const compra = await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 25000,
    data: dia(0),
    descricao: `Padaria ${s}`,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
  });
  const parcelado = await api.criar("/api/parcelamentos", {
    id: randomUUID(),
    valor_total_centavos: 30000,
    parcelas: 3,
    descricao: `Sofá ${s}`,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
    data: dia(0),
  });
  return { s, api, cartao, compra, parcelado };
}

test("a fatura lê as compras do servidor, mesmo sem elas na lista guardada, e guarda a resposta para quando não há internet", async ({ page, context }) => {
  const { s, cartao, compra } = await prepararCartao(page);
  await aparelhoSemALista(page);

  await page.goto(`/#/cartoes/${cartao.id}/${compra.fatura_mes}`);
  await page.reload();
  await expect(page.getByRole("listitem").filter({ hasText: `Padaria ${s}` })).toBeVisible();

  // Sem internet, a tela mostra a última leitura.
  await context.setOffline(true);
  await page.evaluate(() => (location.hash = "#/cartoes"));
  await page.evaluate(([c, m]) => (location.hash = `#/cartoes/${c}/${m}`), [cartao.id, compra.fatura_mes]);
  await expect(page.getByRole("listitem").filter({ hasText: `Padaria ${s}` })).toBeVisible();
  await expect(page.getByText("Sem internet: as compras são as da última leitura.")).toBeVisible();
  await context.setOffline(false);
});

test("a fatura nunca lida e sem internet diz que precisa de internet, em vez de mostrar 'Nenhuma compra'", async ({ page, context }) => {
  const { cartao, compra } = await prepararCartao(page);
  await aparelhoSemALista(page);
  await page.goto("/#/cartoes");
  await expect(page.getByRole("heading", { name: "Cartões", level: 2 })).toBeVisible();

  await context.setOffline(true);
  await page.evaluate(([c, m]) => (location.hash = `#/cartoes/${c}/${m}`), [cartao.id, compra.fatura_mes]);
  await expect(page.getByText("Sem internet: as compras desta fatura precisam de internet.")).toBeVisible();
  await expect(page.getByText("Nenhuma compra nesta fatura.")).toHaveCount(0);
  await context.setOffline(false);
});

test("o Mês abre o Ranking com os lançamentos do servidor, mesmo sem eles na lista guardada", async ({ page }) => {
  const { s, compra } = await prepararCartao(page);
  await aparelhoSemALista(page);

  await page.goto(`/#/mes/${compra.mes.slice(0, 7)}`);
  await page.reload();
  const ranking = page.getByRole("region", { name: "Ranking" });
  await ranking.getByRole("button", { name: new RegExp(`Mercado ${s}`) }).click();
  await expect(page.getByRole("dialog", { name: `Mercado ${s}` })).toContainText(`Padaria ${s}`);
});

test("o parcelamento lista todas as parcelas do servidor, mesmo sem elas na lista guardada", async ({ page, context }) => {
  const { s, parcelado } = await prepararCartao(page);
  await aparelhoSemALista(page);

  await page.goto(`/#/parcelamento/${parcelado.id}`);
  await page.reload();
  const parcelas = page.getByRole("list", { name: `Parcelas de Sofá ${s}` }).getByRole("listitem");
  await expect(parcelas).toHaveCount(3);

  await context.setOffline(true);
  await page.evaluate(() => (location.hash = "#/hoje"));
  await page.evaluate((id) => (location.hash = `#/parcelamento/${id}`), parcelado.id);
  await expect(parcelas).toHaveCount(3);
  await expect(page.getByText("Sem internet: as parcelas são as da última leitura.")).toBeVisible();
  await context.setOffline(false);
});

test("a compra não enviada aparece na fatura sem internet, junto com a leitura guardada", async ({ page, context }) => {
  const { s, cartao, compra } = await prepararCartao(page);
  await aparelhoSemALista(page);
  await page.goto(`/#/cartoes/${cartao.id}/${compra.fatura_mes}`);
  await page.reload();
  await expect(page.getByRole("listitem").filter({ hasText: `Padaria ${s}` })).toBeVisible();

  await context.setOffline(true);
  await lancar(page, { teclas: ["9", "00"], conta: `Visa ${s}`, categoria: `Mercado ${s}`, descricao: `Lanche ${s}` });
  await page.evaluate(([c, m]) => (location.hash = `#/cartoes/${c}/${m}`), [cartao.id, compra.fatura_mes]);
  await expect(page.getByRole("listitem").filter({ hasText: `Lanche ${s}` })).toContainText("⏳ não enviado");
  await expect(page.getByRole("listitem").filter({ hasText: `Padaria ${s}` })).toBeVisible();
  await context.setOffline(false);
});
