import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { cadastrar } from "./lancar";
import { soltarRotas } from "./rotas";

test.afterEach(async ({ page }) => {
  await soltarRotas(page);
});

test.use({ timezoneId: "America/Sao_Paulo", serviceWorkers: "block" });

const daquiA = (dias: number) => new Date(Date.now() + dias * 86_400_000).toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });
const AVISO = "A vez de janeiro não foi gerada porque a fatura já estava paga.";

/** Uma regra mensal pela API; o aviso do ticket 192 é posto na leitura pela rota, que também atende a dispensa. */
async function prepararRegra(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, casa, descricao] = [`Corrente ${s}`, `Casa ${s}`, `Luz ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", casa, "despesa");
  const api = await apiDaPagina(page);
  const contaId = (await api.ler("/api/contas")).find((c: { nome: string }) => c.nome === conta).id;
  const casaId = (await api.ler("/api/categorias")).find((c: { nome: string }) => c.nome === casa).id;
  const regra = await api.criar("/api/recorrencias", {
    id: crypto.randomUUID(),
    tipo: "despesa",
    valor_centavos: 18990,
    tipo_do_valor: "fixo",
    descricao,
    conta_id: contaId,
    categoria_ids: [casaId],
    inicio: daquiA(5),
    a_cada: 1,
    unidade: "meses",
    vezes: 2,
  });
  return { descricao, regra };
}

async function abrirRegra(page: Page, descricao: string) {
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Histórico" }).click();
  const l = page.getByRole("listitem").filter({ hasText: descricao }).filter({ hasText: "R$" }).first();
  await l.getByLabel(`Mais ações ${descricao}`).click();
  await l.getByRole("link", { name: `Recorrência ${descricao}` }).click();
  await expect(page.getByRole("heading", { name: "Recorrência", level: 2 })).toBeVisible();
}

test("a tela da regra mostra o aviso da ocorrência pulada e o dispensa", async ({ page }) => {
  const { descricao, regra } = await prepararRegra(page);
  let aviso: string | null = AVISO;
  const dispensas: string[] = [];
  await page.route("**/api/recorrencias", async (rota) => {
    if (rota.request().method() !== "GET") return rota.fallback();
    const resposta = await rota.fetch();
    const regras = (await resposta.json()).map((r: { id: string }) => (r.id === regra.id ? { ...r, aviso_da_fatura_paga: aviso } : r));
    await rota.fulfill({ response: resposta, json: regras });
  });
  await page.route(`**/api/recorrencias/${regra.id}/aviso-da-fatura-paga`, async (rota) => {
    dispensas.push(rota.request().method());
    aviso = null;
    await rota.fulfill({ status: 204 });
  });

  await abrirRegra(page, descricao);
  await expect(page.getByText(AVISO)).toBeVisible();
  await page.getByRole("button", { name: "Entendi" }).click();
  await expect(page.getByText(AVISO)).toHaveCount(0);
  expect(dispensas).toEqual(["DELETE"]);
});

test("a regra sem aviso não mostra nada", async ({ page }) => {
  const { descricao } = await prepararRegra(page);
  await abrirRegra(page, descricao);
  await expect(page.getByRole("button", { name: "Entendi" })).toHaveCount(0);
});
