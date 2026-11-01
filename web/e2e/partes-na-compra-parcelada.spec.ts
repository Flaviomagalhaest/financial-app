import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { digitar } from "./lancar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

/** Entra e prepara pela API uma conta e duas categorias. */
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
  await page.reload();
  return { api, conta, roupa, casa, nomes };
}

const parte = (page: Page, n: number) => page.getByRole("group", { name: `Parte ${n}`, exact: true });
const aba = (page: Page, nome: string) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome }).click();

/** A 1ª parcela daqui a um mês: todas previstas, nenhuma pulada. */
function daquiAUmMes(): string {
  const dia = new Date();
  dia.setUTCMonth(dia.getUTCMonth() + 1, 10);
  return dia.toISOString().slice(0, 10);
}

test("lança a compra parcelada dividida em partes e cada parcela se divide na proporção delas", async ({ page }) => {
  const { api, nomes } = await preparar(page);
  await aba(page, "Hoje");
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();

  // R$ 300,00 em 3x no boleto: R$ 200,00 de roupa e R$ 100,00 de casa.
  await digitar(page, "3", "00", "00");
  await page.getByRole("button", { name: nomes.conta }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição", { exact: true }).fill(nomes.compra);
  await page.getByRole("group", { name: "Repete?" }).getByRole("button", { name: "Parcelado" }).click();
  await page.getByLabel("Parcelas").fill("3");
  await page.getByRole("button", { name: "Pronto" }).click();

  await page.getByRole("button", { name: "Dividir em partes" }).click();
  await parte(page, 1).getByLabel("Descrição da parte").fill("Camisa");
  await parte(page, 1).getByLabel("Valor da parte").fill("200,00");
  await parte(page, 1).getByRole("button", { name: nomes.roupa }).click();
  await parte(page, 2).getByLabel("Descrição da parte").fill("Toalha");
  await parte(page, 2).getByRole("button", { name: nomes.casa }).click();
  await expect(parte(page, 2).getByLabel("Valor de Toalha")).toContainText("R$ 100,00");
  // O "Repete?" continua na folha: a compra parcelada também se divide.
  await expect(page.getByRole("button", { name: /^Detalhes/ })).toContainText("3x");

  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  // Cada parcela, uma linha que abre as partes dela, na proporção da compra.
  const parcelas = page.getByRole("listitem").filter({ hasText: nomes.compra }).filter({ hasText: /\d\d\/03/ });
  await expect(parcelas).toHaveCount(3);
  const primeira = parcelas.first();
  await expect(primeira).toContainText("R$ 100,00");
  await primeira.getByText("2 partes").click();
  const partes = primeira.getByRole("list", { name: `Partes de ${nomes.compra}` });
  await expect(partes.getByRole("listitem").nth(0)).toContainText("Camisa");
  await expect(partes.getByRole("listitem").nth(0)).toContainText("R$ 66,67");
  await expect(partes.getByRole("listitem").nth(1)).toContainText("R$ 33,33");

  const [gravado] = (await api.ler("/api/parcelamentos")).filter((p: { descricao: string }) => p.descricao === nomes.compra);
  expect(gravado.categoria_ids).toEqual([]);
  expect(gravado.partes.map((p: { valor_centavos: number }) => p.valor_centavos)).toEqual([20000, 10000]);
});

test("a parcela que muda de valor se redivide na proporção, e mudar as partes em todas chega às outras", async ({ page }) => {
  const { api, conta, roupa, casa, nomes } = await preparar(page);
  const id = crypto.randomUUID();
  await api.criar("/api/parcelamentos", {
    id,
    valor_total_centavos: 30000,
    parcelas: 3,
    data: daquiAUmMes(),
    descricao: nomes.compra,
    conta_id: conta.id,
    categoria_ids: [],
    partes: [
      { id: crypto.randomUUID(), descricao: "Camisa", valor_centavos: 20000, categoria_ids: [roupa.id], tags: [] },
      { id: crypto.randomUUID(), descricao: "Toalha", valor_centavos: 10000, categoria_ids: [casa.id], tags: [] },
    ],
  });
  const doParcelamento = async () =>
    ((await api.ler("/api/lancamentos")) as { parcelamento_id: string; parcela: number; valor_centavos: number; partes: { valor_centavos: number; descricao: string }[] }[])
      .filter((l) => l.parcelamento_id === id)
      .sort((a, b) => a.parcela - b.parcela);
  await page.reload();
  await aba(page, "Histórico");
  const parcela = (n: string) => page.getByRole("listitem").filter({ hasText: `${nomes.compra} ${n}` });

  // Só o valor da 2ª, só nela: as partes acompanham na mesma proporção.
  await parcela("02/03").getByRole("link", { name: `Editar ${nomes.compra}` }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 100,00");
  await expect(parte(page, 2).getByLabel("Valor de Toalha")).toContainText("R$ 33,33");
  await digitar(page, "Apagar", "Apagar", "Apagar", "Apagar", "Apagar", "1", "5", "0", "0", "0");
  await expect(parte(page, 1).getByLabel("Valor da parte")).toHaveValue("100,00");
  await expect(parte(page, 2).getByLabel("Valor de Toalha")).toContainText("R$ 50,00");
  await page.getByRole("button", { name: "Salvar" }).click();
  await page.getByRole("group", { name: "Mudar quais parcelas?" }).getByRole("button", { name: "Só esta" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect.poll(async () => (await doParcelamento()).map((l) => l.partes.map((p) => p.valor_centavos))).toEqual([
    [6667, 3333],
    [10000, 5000],
    [6667, 3333],
  ]);

  // As partes de novo na 1ª, em todas: a 2ª, com o valor dela, também se divide pela proporção nova.
  await parcela("01/03").getByRole("link", { name: `Editar ${nomes.compra}` }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 100,00");
  await parte(page, 1).getByLabel("Valor da parte").fill("50,00");
  await expect(parte(page, 2).getByLabel("Valor de Toalha")).toContainText("R$ 50,00");
  await page.getByRole("button", { name: "Salvar" }).click();
  await page.getByRole("group", { name: "Mudar quais parcelas?" }).getByRole("button", { name: "Todas (inclusive as já realizadas)" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect.poll(async () => (await doParcelamento()).map((l) => l.partes.map((p) => p.valor_centavos))).toEqual([
    [5000, 5000],
    [7500, 7500],
    [5000, 5000],
  ]);

  // A tela do parcelamento mostra as partes no lugar das categorias.
  await page.evaluate((destino) => (window.location.hash = destino), `#/parcelamento/${id}`);
  const daRegra = page.getByRole("list", { name: "Partes do parcelamento" });
  await expect(daRegra.getByRole("listitem")).toHaveCount(2);
  await expect(daRegra.getByRole("listitem").nth(0)).toContainText("Camisa");
  await expect(daRegra.getByRole("listitem").nth(0)).toContainText("50%");
  await expect(page.getByRole("heading", { name: "Categorias" })).toHaveCount(0);
});
