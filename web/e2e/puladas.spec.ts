import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { cadastrar, digitar } from "./lancar";

const [anoDeHoje, mesDeHoje, diaDeHoje] = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date()).split("-").map(Number);

/** O dia 28 (ou o de hoje, se menor) de `meses` meses atrás, como `AAAA-MM-DD`: existe em todo mês. */
function mesesAtras(meses: number): string {
  return new Date(Date.UTC(anoDeHoje, mesDeHoje - 1 - meses, Math.min(diaDeHoje, 28))).toISOString().slice(0, 10);
}

/** Depois do dia 28 a ocorrência do mês atual (dia 28) também já passou. */
const extra = diaDeHoje > 28 ? 1 : 0;
const antesDeHoje = (n: number, um: string, varios: string) => (n === 1 ? `1 ${um} não será lançada: cai antes de hoje.` : `${n} ${varios} não serão lançadas: caem antes de hoje.`);

async function prepararCasal(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, casa] = [`Corrente ${s}`, `Casa ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", casa, "despesa");
  return { s, conta, casa };
}

async function abrirDetalhes(page: Page, { conta, categoria, repete }: { conta: string; categoria: string; repete: "Parcelado" | "Recorrente" }) {
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, "1", "00", "00");
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: categoria }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByRole("group", { name: "Repete?" }).getByRole("button", { name: repete }).click();
}

test("a folha avisa quantas ocorrências da recorrência caem antes de hoje", async ({ page }) => {
  const { conta, casa } = await prepararCasal(page);
  await abrirDetalhes(page, { conta, categoria: casa, repete: "Recorrente" });
  const aviso = page.getByRole("dialog").locator(".aviso");
  await expect(aviso).toHaveCount(0);

  // Todo mês, desde há 3 meses: as de há 3, 2 e 1 meses ficaram para trás; a de hoje, não.
  await page.getByLabel("Outra data").fill(mesesAtras(3));
  await expect(aviso).toHaveText(antesDeHoje(3 + extra, "ocorrência", "ocorrências"));

  await page.getByLabel("Outra data").fill(mesesAtras(1));
  await expect(aviso).toHaveText(antesDeHoje(1 + extra, "ocorrência", "ocorrências"));

  await page.getByRole("group", { name: "Termina" }).getByRole("button", { name: "Depois de" }).click();
  await page.getByLabel("Vezes").fill("5");
  await page.getByLabel("Outra data").fill(mesesAtras(3));
  // O fim por vezes não corta o passado: 5 vezes desde há 3 meses ainda deixam 3 para trás.
  await expect(aviso).toHaveText(antesDeHoje(3 + extra, "ocorrência", "ocorrências"));
  await page.getByLabel("Vezes").fill("2");
  await expect(aviso).toHaveText(antesDeHoje(2, "ocorrência", "ocorrências"));

  await page.getByLabel("Outra data").fill(mesesAtras(0));
  await expect(aviso).toHaveCount(extra ? 1 : 0);
});

test("a folha avisa as parcelas do boleto antes de hoje, e a tela do parcelamento mostra as puladas", async ({ page }) => {
  const { s, conta, casa } = await prepararCasal(page);
  await abrirDetalhes(page, { conta, categoria: casa, repete: "Parcelado" });
  await page.getByLabel("Descrição").fill(`Sofá ${s}`);
  await page.getByLabel("Parcelas").fill("4");
  const aviso = page.getByRole("dialog").locator(".aviso");
  await expect(aviso).toHaveCount(0);
  await page.getByLabel("Outra data").fill(mesesAtras(2));
  await expect(aviso).toHaveText(antesDeHoje(2 + extra, "parcela", "parcelas"));
  await page.getByLabel("Outra data").fill(mesesAtras(1));
  await expect(aviso).toHaveText(antesDeHoje(1 + extra, "parcela", "parcelas"));
  await page.getByLabel("Outra data").fill(mesesAtras(2));

  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  const api = await apiDaPagina(page);
  await expect.poll(async () => (await api.ler("/api/parcelamentos")).filter((p: { descricao: string }) => p.descricao === `Sofá ${s}`).length).toBe(1);
  const [gravado] = (await api.ler("/api/parcelamentos")).filter((p: { descricao: string }) => p.descricao === `Sofá ${s}`);
  expect(gravado.parcelas_puladas).toBe(2 + extra);

  await page.goto(`/#/parcelamento/${gravado.id}`);
  await expect(page.getByText(`${2 + extra} parcelas não foram lançadas: venciam antes de hoje`)).toBeVisible();
});

test("o cartão não pula parcela: a folha não avisa", async ({ page }) => {
  const { s, casa } = await prepararCasal(page);
  const visa = `Visa ${s}`;
  const api = await apiDaPagina(page);
  await api.criar("/api/cartoes", { nome: visa, dia_fechamento: 10, dia_vencimento: 20 });
  await page.reload();
  await abrirDetalhes(page, { conta: visa, categoria: casa, repete: "Parcelado" });
  await page.getByLabel("Outra data").fill(mesesAtras(2));
  await expect(page.getByRole("dialog").locator(".aviso")).toHaveCount(0);
});
