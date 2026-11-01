import { expect, test, type Locator, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { digitar } from "./lancar";

// Partes na recorrência (ticket 140, ADR 0022): o combo de celular e internet numa conta só.
test.use({ timezoneId: "America/Sao_Paulo", serviceWorkers: "block" });

const aba = (page: Page, nome: string) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome }).click();
const historico = (page: Page) => expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
/** Os lançamentos com esse texto, sem as mudanças não enviadas (que não mostram valor). */
const linha = (page: Page, texto: string) => page.getByRole("listitem").filter({ hasText: texto }).filter({ hasText: "R$" });
const parte = (page: Page, n: number) => page.getByRole("group", { name: `Parte ${n}`, exact: true });
/** Daqui a `dias` dias em São Paulo (`AAAA-MM-DD`). */
const daquiA = (dias: number) => new Date(Date.now() + dias * 86_400_000).toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });

type Parte = { valor_centavos: number };
type ComPartes = { descricao: string; valor_centavos: number; ocorrencia: number; partes: Parte[] };

/** Entra e prepara pela API uma conta e as categorias Celular e Internet. */
async function preparar(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const nomes = { conta: `Corrente ${s}`, celular: `Celular ${s}`, internet: `Internet ${s}`, combo: `Combo ${s}` };
  await page.goto("/#/historico");
  await entrar(page);
  await historico(page);
  const api = await apiDaPagina(page);
  const conta = await api.criar("/api/contas", { nome: nomes.conta, tipo: "corrente" });
  const celular = await api.criar("/api/categorias", { nome: nomes.celular, tipo: "despesa" });
  const internet = await api.criar("/api/categorias", { nome: nomes.internet, tipo: "despesa" });
  await page.reload();
  return { api, nomes, conta, celular, internet };
}

/** Os previstos da regra, da 1ª à última vez, com o valor de cada parte. */
async function previstos(api: Awaited<ReturnType<typeof apiDaPagina>>, descricao: string) {
  const lidos: ComPartes[] = await api.ler("/api/lancamentos");
  return lidos
    .filter((l) => l.descricao === descricao)
    .sort((a, b) => a.ocorrencia - b.ocorrencia)
    .map((l) => [l.valor_centavos, l.partes.map((p) => p.valor_centavos)]);
}

/** Pelo "⋯" de um lançamento da recorrência, abre a tela dela a partir dele. */
async function abrirRecorrencia(page: Page, lancamento: Locator, descricao: string) {
  await lancamento.getByLabel(`Mais ações ${descricao}`).click();
  await lancamento.getByRole("link", { name: `Recorrência ${descricao}` }).click();
  await expect(page.getByRole("heading", { name: "Recorrência", level: 2 })).toBeVisible();
}

test("lança a recorrência dividida em partes, e cada ocorrência aparece numa linha só que abre as partes", async ({ page }) => {
  const { api, nomes } = await preparar(page);
  await aba(page, "Hoje");
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();

  // R$ 100,00 por mês, três vezes, no combo.
  await digitar(page, "1", "00", "00");
  await page.getByRole("button", { name: nomes.conta }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição", { exact: true }).fill(nomes.combo);
  await page.getByRole("group", { name: "Repete?" }).getByRole("button", { name: "Recorrente" }).click();
  await page.getByRole("group", { name: "Termina" }).getByRole("button", { name: "Depois de" }).click();
  await page.getByLabel("Vezes").fill("3");
  await page.getByRole("button", { name: "Pronto" }).click();

  await page.getByRole("button", { name: "Dividir em partes" }).click();
  await parte(page, 1).getByLabel("Descrição da parte").fill("Celular");
  await parte(page, 1).getByLabel("Valor da parte").fill("60,00");
  await parte(page, 1).getByRole("button", { name: nomes.celular }).click();
  await parte(page, 2).getByLabel("Descrição da parte").fill("Internet");
  await parte(page, 2).getByRole("button", { name: nomes.internet }).click();
  await expect(parte(page, 2).getByLabel("Valor de Internet")).toContainText("R$ 40,00");
  await page.getByRole("button", { name: "Salvar" }).click();
  await historico(page);

  const linhas = linha(page, nomes.combo);
  await expect(linhas).toHaveCount(3);
  await expect(linhas.first()).toContainText("− R$ 100,00");
  await linhas.first().getByText("2 partes").click();
  const partes = linhas.first().getByRole("list", { name: `Partes de ${nomes.combo}` });
  await expect(partes.getByRole("listitem").nth(0)).toContainText("Celular");
  await expect(partes.getByRole("listitem").nth(0)).toContainText("R$ 60,00");
  await expect(partes.getByRole("listitem").nth(1)).toContainText(nomes.internet);

  const [regra] = (await api.ler("/api/recorrencias")).filter((r: { descricao: string }) => r.descricao === nomes.combo);
  expect(regra.categoria_ids).toEqual([]);
  expect(regra.partes.map((p: Parte) => p.valor_centavos)).toEqual([6000, 4000]);
  expect(await previstos(api, nomes.combo)).toEqual(Array(3).fill([10000, [6000, 4000]]));
});

test("o valor do mês redivide as partes, e mudar o valor e as partes daqui para frente não alcança o mês mudado à mão", async ({ page }) => {
  const { api, nomes, conta, celular, internet } = await preparar(page);
  await api.criar("/api/recorrencias", {
    id: crypto.randomUUID(),
    tipo: "despesa",
    valor_centavos: 10000,
    tipo_do_valor: "estimado",
    descricao: nomes.combo,
    conta_id: conta.id,
    categoria_ids: [],
    partes: [
      { id: crypto.randomUUID(), descricao: "Celular", valor_centavos: 6000, categoria_ids: [celular.id] },
      { id: crypto.randomUUID(), descricao: "Internet", valor_centavos: 4000, categoria_ids: [internet.id] },
    ],
    inicio: daquiA(5),
    a_cada: 1,
    unidade: "meses",
    vezes: 3,
  });
  await page.reload();
  // Do mais novo ao mais antigo: a 3ª, a 2ª e a 1ª vez.
  const linhas = linha(page, nomes.combo);
  await expect(linhas).toHaveCount(3);

  // Só a 2ª: a conta veio de R$ 150,00, e as partes se dividem na proporção.
  await abrirRecorrencia(page, linhas.nth(1), nomes.combo);
  await page.getByRole("link", { name: "Mudar só este mês" }).click();
  await expect(parte(page, 1).getByLabel("Valor da parte")).toHaveValue("60,00");
  await digitar(page, "Apagar", "Apagar", "Apagar", "Apagar", "Apagar", "1", "5", "0", "00");
  await expect(parte(page, 1).getByLabel("Valor da parte")).toHaveValue("90,00");
  await expect(parte(page, 2).getByLabel("Valor de Internet")).toContainText("R$ 60,00");
  await page.getByRole("button", { name: "Salvar" }).click();
  await historico(page);
  await expect(linhas.nth(1)).toContainText("− R$ 150,00");
  await expect.poll(() => previstos(api, nomes.combo)).toEqual([
    [10000, [6000, 4000]],
    [15000, [9000, 6000]],
    [10000, [6000, 4000]],
  ]);

  // Daqui para frente, desde a 1ª: o valor novo divide as partes da regra, que se mudam também.
  await abrirRecorrencia(page, linhas.nth(2), nomes.combo);
  await page.getByRole("textbox", { name: "Valor", exact: true }).fill("120,00");
  await expect(parte(page, 1).getByLabel("Valor da parte")).toHaveValue("72,00");
  await expect(parte(page, 2).getByLabel("Valor de Internet")).toContainText("R$ 48,00");
  await parte(page, 1).getByLabel("Valor da parte").fill("70,00");
  await expect(parte(page, 2).getByLabel("Valor de Internet")).toContainText("R$ 50,00");
  await page.getByRole("button", { name: "Salvar daqui para frente" }).click();
  await historico(page);

  await expect(linhas.nth(0)).toContainText("− R$ 120,00");
  await expect(linhas.nth(1)).toContainText("− R$ 150,00");
  await expect.poll(() => previstos(api, nomes.combo)).toEqual([
    [12000, [7000, 5000]],
    [15000, [9000, 6000]],
    [12000, [7000, 5000]],
  ]);
  const [regra] = (await api.ler("/api/recorrencias")).filter((r: { descricao: string }) => r.descricao === nomes.combo);
  expect(regra.partes.map((p: Parte) => p.valor_centavos)).toEqual([7000, 5000]);
});

test("tirar a penúltima parte daqui para frente junta a regra com a classificação da parte que ficou", async ({ page }) => {
  const { api, nomes, conta, celular, internet } = await preparar(page);
  await api.criar("/api/recorrencias", {
    id: crypto.randomUUID(),
    tipo: "despesa",
    valor_centavos: 10000,
    tipo_do_valor: "fixo",
    descricao: nomes.combo,
    conta_id: conta.id,
    categoria_ids: [],
    partes: [
      { id: crypto.randomUUID(), descricao: "Celular", valor_centavos: 6000, categoria_ids: [celular.id] },
      { id: crypto.randomUUID(), descricao: "Internet", valor_centavos: 4000, categoria_ids: [internet.id] },
    ],
    inicio: daquiA(5),
    a_cada: 1,
    unidade: "meses",
    vezes: 2,
  });
  await page.reload();
  const linhas = linha(page, nomes.combo);
  await expect(linhas).toHaveCount(2);

  await abrirRecorrencia(page, linhas.nth(1), nomes.combo);
  await page.getByRole("button", { name: "Tirar Celular" }).click();
  await expect(page.getByRole("button", { name: nomes.internet })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Salvar daqui para frente" }).click();
  await historico(page);

  await expect
    .poll(async () => (await api.ler("/api/recorrencias")).filter((r: { descricao: string }) => r.descricao === nomes.combo).map((r: { partes: Parte[]; categoria_ids: string[] }) => [r.partes.length, r.categoria_ids]))
    .toEqual([[0, [internet.id]]]);
  await expect(linhas.first().getByText("2 partes")).toHaveCount(0);
});
