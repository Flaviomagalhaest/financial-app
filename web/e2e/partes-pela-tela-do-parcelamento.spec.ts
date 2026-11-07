import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";

// Ticket 158: a tela do parcelamento divide, muda e junta as partes, em valor do total ou da parcela.
test.use({ timezoneId: "America/Sao_Paulo" });

async function preparar(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const nomes = { conta: `Corrente ${s}`, roupa: `Roupa ${s}`, casa: `Casa ${s}`, compra: `Loja ${s}` };
  await page.goto("/#/historico");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  const api = await apiDaPagina(page);
  const conta = await api.criar("/api/contas", { nome: nomes.conta, tipo: "corrente" });
  const roupa = await api.criar("/api/categorias", { nome: nomes.roupa, tipo: "despesa" });
  const casa = await api.criar("/api/categorias", { nome: nomes.casa, tipo: "despesa" });
  return { api, conta, roupa, casa, nomes };
}

const parte = (page: Page, n: number) => page.getByRole("group", { name: `Parte ${n}`, exact: true });

/** A 1ª parcela daqui a um mês: todas previstas. */
function daquiAUmMes(): string {
  const dia = new Date();
  dia.setUTCMonth(dia.getUTCMonth() + 1, 10);
  return dia.toISOString().slice(0, 10);
}

type Lido = { parcelamento_id: string; parcela: number; categoria_ids: string[]; partes: { valor_centavos: number; descricao: string }[] };

test("divide, muda e junta as partes pela tela do parcelamento", async ({ page }) => {
  const { api, conta, roupa, casa, nomes } = await preparar(page);
  const id = crypto.randomUUID();
  // R$ 300,00 em 3x, sem partes.
  await api.criar("/api/parcelamentos", { id, valor_total_centavos: 30000, parcelas: 3, data: daquiAUmMes(), descricao: nomes.compra, conta_id: conta.id, categoria_ids: [roupa.id] });
  const doParcelamento = async () =>
    ((await api.ler("/api/lancamentos")) as Lido[]).filter((l) => l.parcelamento_id === id).sort((a, b) => a.parcela - b.parcela);
  const abrir = async () => {
    await page.evaluate((destino) => (window.location.hash = destino), `#/parcelamento/${id}`);
    await expect(page.getByLabel("Descrição", { exact: true })).toHaveValue(nomes.compra);
  };
  await page.reload();
  await abrir();

  // Dividir: a 1ª parte fica com a categoria que o parcelamento tinha; R$ 200,00 do total nela.
  await page.getByRole("button", { name: "Dividir em partes" }).click();
  await expect(page.getByRole("heading", { name: "Categorias" })).toHaveCount(0);
  await expect(parte(page, 1).getByRole("button", { name: nomes.roupa })).toHaveAttribute("aria-pressed", "true");
  await parte(page, 1).getByLabel("Descrição da parte").fill("Camisa");
  await parte(page, 1).getByLabel("Valor da parte").fill("200,00");
  await parte(page, 2).getByLabel("Descrição da parte").fill("Toalha");
  await parte(page, 2).getByRole("button", { name: nomes.casa }).click();
  await expect(parte(page, 2).getByLabel("Valor de Toalha")).toContainText("R$ 100,00");

  // Em valor da parcela, as partes se convertem na mesma proporção.
  await page.getByRole("group", { name: "O valor é" }).getByRole("button", { name: "O da parcela" }).click();
  await expect(page.getByLabel("Valor da parcela")).toHaveValue("100,00");
  await expect(parte(page, 1).getByLabel("Valor da parte")).toHaveValue("66,67");
  await expect(parte(page, 2).getByLabel("Valor de Toalha")).toContainText("R$ 33,33");
  await page.getByRole("button", { name: "Salvar correção" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect.poll(async () => (await doParcelamento()).map((l) => l.partes.map((p) => p.valor_centavos))).toEqual([
    [6667, 3333],
    [6667, 3333],
    [6667, 3333],
  ]);

  // Mudar: a tela abre com as partes somando o total; R$ 150,00 + R$ 150,00.
  await abrir();
  await expect(parte(page, 1).getByLabel("Valor da parte")).toHaveValue("200,01");
  await parte(page, 1).getByLabel("Valor da parte").fill("150,00");
  await expect(parte(page, 2).getByLabel("Valor de Toalha")).toContainText("R$ 150,00");
  await page.getByRole("button", { name: "Salvar correção" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect.poll(async () => (await doParcelamento()).map((l) => l.partes.map((p) => p.valor_centavos))).toEqual([
    [5000, 5000],
    [5000, 5000],
    [5000, 5000],
  ]);

  // Juntar: tirar a Camisa deixa a Toalha, e o parcelamento volta a ter a categoria dela.
  await abrir();
  await page.getByRole("button", { name: "Tirar Camisa" }).click();
  await expect(page.getByRole("heading", { name: "Categorias" })).toBeVisible();
  await page.getByRole("button", { name: "Salvar correção" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect.poll(async () => (await doParcelamento()).map((l) => [l.partes.length, l.categoria_ids])).toEqual([
    [0, [casa.id]],
    [0, [casa.id]],
    [0, [casa.id]],
  ]);
});
