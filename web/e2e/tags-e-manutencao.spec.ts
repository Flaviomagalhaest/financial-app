import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";
import { cadastrar } from "./lancar";

test.use({ timezoneId: "America/Sao_Paulo" });

/** Cria direto pela API, com o token da página (a tela não cadastra lançamento sem passar pelo teclado). */
async function tokenDaPagina(page: Page): Promise<string> {
  const pedido = page.waitForRequest((r) => r.url().includes("/api/") && !!r.headers().authorization);
  await page.reload();
  return (await pedido).headers().authorization;
}

const linha = (page: Page, nome: string) => page.getByRole("listitem").filter({ hasText: nome });

test("mantém as tags: cria, renomeia, arquiva, junta e exclui só a que não tem lançamentos", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, comida, viagem, ferias, avulsa] = [`Conta ${s}`, `Comida ${s}`, `viagem ${s}`, `férias ${s}`, `avulsa ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", comida, "despesa");
  const headers = { authorization: await tokenDaPagina(page) };
  const api = async (metodo: "post" | "get", caminho: string, data?: object) => {
    const r = await page.request[metodo](caminho, { headers, data });
    expect(r.ok(), await r.text()).toBe(true);
    return r.json();
  };
  const contas = await api("get", "/api/contas");
  const categorias = await api("get", "/api/categorias");
  const lancar = (tags: string[]) =>
    api("post", "/api/lancamentos", {
      id: randomUUID(),
      tipo: "despesa",
      valor_centavos: 1000,
      data: new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date()),
      descricao: `Compra ${s}`,
      conta_id: contas.find((c: { nome: string }) => c.nome === conta).id,
      categoria_ids: [categorias.find((c: { nome: string }) => c.nome === comida).id],
      tags,
    });
  await lancar([viagem]);
  await lancar([ferias]);
  await page.reload();

  // As tags dos lançamentos aparecem na lista; criar uma sem lançamento.
  const tags = page.getByRole("region", { name: "Tags" });
  await expect(tags.getByRole("listitem").filter({ hasText: viagem })).toBeVisible();
  await tags.getByLabel("Nome da nova tag").fill(avulsa);
  await tags.getByRole("button", { name: "Criar tag" }).click();
  await expect(linha(page, avulsa)).toBeVisible();

  // Renomear.
  await page.getByRole("button", { name: `Renomear ${viagem}` }).click();
  await page.getByLabel(`Novo nome de ${viagem}`).fill(`viagem 2026 ${s}`);
  await page.getByRole("button", { name: "Salvar nome" }).click();
  await expect(linha(page, `viagem 2026 ${s}`)).toBeVisible();

  // Arquivar e desarquivar.
  await page.getByRole("button", { name: `Arquivar ${avulsa}` }).click();
  await expect(linha(page, avulsa)).toContainText("(arquivada)");
  await page.getByRole("button", { name: `Desarquivar ${avulsa}` }).click();
  await expect(linha(page, avulsa)).not.toContainText("(arquivada)");

  // Excluir recusa a tag com lançamentos e aceita a sem.
  await page.getByRole("button", { name: `Excluir ${ferias}` }).click();
  await expect(page.getByRole("alert")).toContainText("lançamentos");
  await expect(linha(page, ferias)).toBeVisible();
  await page.getByRole("button", { name: `Excluir ${avulsa}` }).click();
  await expect(linha(page, avulsa)).toHaveCount(0);

  // Juntar move os lançamentos para o destino e some com a origem.
  await page.getByRole("button", { name: `Juntar ${ferias}` }).click();
  await page.getByLabel(`Juntar ${ferias} em`).selectOption({ label: `viagem 2026 ${s}` });
  await page.getByRole("button", { name: "Confirmar junção" }).click();
  await expect(linha(page, ferias)).toHaveCount(0);
  const historico = await api("get", "/api/lancamentos");
  const dessa = historico.filter((l: { descricao: string }) => l.descricao === `Compra ${s}`);
  expect(dessa.map((l: { tags: string[] }) => l.tags).flat()).toEqual([`viagem 2026 ${s}`, `viagem 2026 ${s}`]);
});

test("junta e exclui categorias na tela de configuração", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [mercado, supermercado, vazia, conta, salario] = [`Mercado ${s}`, `Atacado ${s}`, `Vazia ${s}`, `Conta ${s}`, `Salário ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  await cadastrar(page, "Nova categoria", supermercado, "despesa");
  await cadastrar(page, "Nova categoria", vazia, "despesa");
  await cadastrar(page, "Nova categoria", salario, "receita");
  const headers = { authorization: await tokenDaPagina(page) };
  const contas = await (await page.request.get("/api/contas", { headers })).json();
  const categorias = await (await page.request.get("/api/categorias", { headers })).json();
  const id = (lista: { nome: string; id: string }[], nome: string) => lista.find((i) => i.nome === nome)!.id;
  const criado = await page.request.post("/api/lancamentos", {
    headers,
    data: {
      id: randomUUID(),
      tipo: "despesa",
      valor_centavos: 500,
      data: new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date()),
      descricao: `Feira ${s}`,
      conta_id: id(contas, conta),
      categoria_ids: [id(categorias, mercado)],
      tags: [],
    },
  });
  expect(criado.ok(), await criado.text()).toBe(true);
  await page.reload();

  // Excluir recusa a categoria com lançamentos e aceita a vazia.
  await page.getByRole("button", { name: `Excluir ${mercado}` }).click();
  await expect(page.getByRole("alert")).toContainText("lançamentos");
  await expect(linha(page, mercado)).toBeVisible();
  await page.getByRole("button", { name: `Excluir ${vazia}` }).click();
  await expect(linha(page, vazia)).toHaveCount(0);

  // Juntar só oferece categorias do mesmo tipo.
  await page.getByRole("button", { name: `Juntar ${mercado}` }).click();
  const destinos = page.getByLabel(`Juntar ${mercado} em`);
  await expect(destinos.getByRole("option", { name: supermercado })).toHaveCount(1);
  await expect(destinos.getByRole("option", { name: salario })).toHaveCount(0);
  await destinos.selectOption({ label: supermercado });
  await page.getByRole("button", { name: "Confirmar junção" }).click();
  await expect(linha(page, mercado)).toHaveCount(0);
  const lancamentos = await (await page.request.get("/api/lancamentos", { headers })).json();
  const feira = lancamentos.find((l: { descricao: string }) => l.descricao === `Feira ${s}`);
  expect(feira.categoria_ids).toEqual([id(categorias, supermercado)]);
});
