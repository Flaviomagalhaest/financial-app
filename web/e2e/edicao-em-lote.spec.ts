import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

type Api = Awaited<ReturnType<typeof apiDaPagina>>;

/** Uma conta e duas categorias com o sufixo `s`, que a busca pelo texto isola dos outros testes. */
async function preparar(api: Api, s: string) {
  const conta = await api.criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const mercado = await api.criar("/api/categorias", { nome: `Mercado ${s}`, tipo: "despesa" });
  const casa = await api.criar("/api/categorias", { nome: `Casa ${s}`, tipo: "despesa" });
  const lancar = (descricao: string, categoria_ids = [mercado.id]) =>
    api.criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos: 5000, data: "2026-03-02", descricao, conta_id: conta.id, categoria_ids, tags: [] });
  return { conta, mercado, casa, lancar };
}

async function buscar(page: Page, texto: string) {
  await page.goto("/#/busca");
  await page.getByLabel("Buscar na descrição").fill(texto);
  // A busca sai quando a pessoa para de digitar: o endereço leva o texto, e só então o resultado é dele.
  await expect(page).toHaveURL(new RegExp(`texto=${texto}`));
  await expect(page.getByLabel("Totais da busca")).toBeVisible();
}

test("marca no resultado, vê a prévia, aplica tudo de uma vez e desfaz", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/busca");
  await entrar(page);
  const api = await apiDaPagina(page);
  const { conta, mercado, lancar } = await preparar(api, s);
  await lancar(`Feira ${s}`);
  await lancar(`Padaria ${s}`);
  await api.criar("/api/parcelamentos", { id: randomUUID(), valor_total_centavos: 90000, parcelas: 3, descricao: `Geladeira ${s}`, conta_id: conta.id, categoria_ids: [mercado.id], data: new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date()) });

  await buscar(page, s);
  const linhas = page.getByRole("list", { name: "Resultado da busca" }).locator(":scope > li");
  await expect(linhas).toHaveCount(3);
  await page.getByRole("button", { name: "Selecionar para editar em lote" }).click();
  await page.getByLabel(`Marcar Feira ${s}`).check();
  await page.getByLabel(`Marcar Geladeira ${s}`).check();
  await expect(page.getByRole("group", { name: "Seleção" })).toContainText("2 marcados");
  await page.getByRole("button", { name: "Editar em lote" }).click();

  const folha = page.getByRole("dialog", { name: "Editar em lote" });
  await folha.getByRole("group", { name: "Categorias de despesa" }).getByRole("button", { name: `Casa ${s}` }).click();
  await folha.getByRole("button", { name: "Ver prévia" }).click();
  const previa = folha.getByRole("region", { name: "Prévia" });
  // A geladeira leva as três parcelas.
  await expect(previa).toContainText("2 compras (4 lançamentos)");
  await expect(previa).toContainText("4 mudam, 0 já estão como pedido.");
  await expect(previa.getByRole("list", { name: "Antes e depois" }).getByRole("listitem").first()).toContainText(`Depois: Mercado ${s}, Casa ${s}`);
  await folha.getByRole("button", { name: "Aplicar em 4 lançamentos" }).click();

  await expect(folha).toBeHidden();
  await expect(page.getByRole("status")).toContainText(`Edição aplicada em 4 lançamentos: Categorias: acrescentar Casa ${s}.`);
  await expect(linhas.filter({ hasText: `Feira ${s}` })).toContainText(`Casa ${s}`);
  await expect(linhas.filter({ hasText: `Padaria ${s}` })).not.toContainText(`Casa ${s}`);

  await page.getByRole("status").getByRole("link", { name: "Desfazer" }).click();
  await expect(page.getByRole("heading", { name: "Edições em lote" })).toBeVisible();
  await page.getByRole("button", { name: `Desfazer Categorias: acrescentar Casa ${s}` }).click();
  await expect(page.getByRole("status")).toContainText(`Desfeita: Categorias: acrescentar Casa ${s}, em 4 lançamentos.`);
  await expect(page.getByRole("button", { name: `Desfazer Categorias: acrescentar Casa ${s}` })).toBeHidden();

  await buscar(page, s);
  await expect(linhas.filter({ hasText: `Feira ${s}` })).not.toContainText(`Casa ${s}`);
});

test("todos do resultado: a prévia recusa o lote que deixaria lançamento sem categoria", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/busca");
  await entrar(page);
  const api = await apiDaPagina(page);
  const { mercado, casa, lancar } = await preparar(api, s);
  await lancar(`Feira ${s}`, [mercado.id, casa.id]);
  await lancar(`Padaria ${s}`);

  await buscar(page, s);
  await page.getByRole("button", { name: "Selecionar para editar em lote" }).click();
  await page.getByRole("button", { name: "Todos do resultado" }).click();
  await expect(page.getByRole("group", { name: "Seleção" })).toContainText("Todos do resultado (2)");
  await page.getByRole("button", { name: "Editar em lote" }).click();

  const folha = page.getByRole("dialog", { name: "Editar em lote" });
  await folha.getByRole("button", { name: "Tirar" }).click();
  await folha.getByRole("group", { name: "Categorias de despesa" }).getByRole("button", { name: `Mercado ${s}` }).click();
  await folha.getByRole("button", { name: "Ver prévia" }).click();

  await expect(folha.getByRole("alert")).toHaveText("o lote deixaria 1 lançamento sem categoria");
  await expect(folha.getByRole("button", { name: /Aplicar/ })).toHaveCount(0);
});

test("a compra com partes muda nas partes, e a prévia mostra cada parte que muda", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/busca");
  await entrar(page);
  const api = await apiDaPagina(page);
  const { conta, mercado, casa } = await preparar(api, s);
  const parte = (descricao: string, valor_centavos: number, categoria_ids: string[]) => ({ id: randomUUID(), descricao, valor_centavos, categoria_ids, tags: [] });
  await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 10000,
    data: "2026-03-02",
    descricao: `Loja ${s}`,
    conta_id: conta.id,
    categoria_ids: [],
    tags: [],
    partes: [parte("Vassoura", 6000, [casa.id]), parte("Arroz", 4000, [mercado.id])],
  });

  await buscar(page, s);
  await page.getByRole("button", { name: "Selecionar para editar em lote" }).click();
  await page.getByLabel(`Marcar Loja ${s}`).check();
  await page.getByRole("button", { name: "Editar em lote" }).click();
  const folha = page.getByRole("dialog", { name: "Editar em lote" });
  await folha.getByRole("group", { name: "Categorias de despesa" }).getByRole("button", { name: `Casa ${s}` }).click();
  await folha.getByRole("button", { name: "Ver prévia" }).click();

  const previa = folha.getByRole("region", { name: "Prévia" });
  await expect(previa).toContainText("1 muda, 0 já estão como pedido.");
  await expect(previa).toContainText("Nas compras com partes, 1 parte muda.");
  const antesEDepois = previa.getByRole("list", { name: "Antes e depois" });
  // A vassoura já está na Casa: só o arroz aparece.
  await expect(antesEDepois.getByLabel("Arroz")).toContainText(`Arroz: Mercado ${s} → Mercado ${s}, Casa ${s}`);
  await expect(antesEDepois.getByLabel("Vassoura")).toHaveCount(0);
  await folha.getByRole("button", { name: "Aplicar em 1 lançamento" }).click();

  await expect(folha).toBeHidden();
  await expect(page.getByRole("status")).toContainText(`Edição aplicada em 1 lançamento: Categorias: acrescentar Casa ${s}.`);
  const [compra] = (await api.ler("/api/lancamentos")).filter((l: { descricao: string }) => l.descricao === `Loja ${s}`);
  expect(compra.partes.map((p: { categoria_ids: string[] }) => p.categoria_ids.sort())).toEqual([[casa.id], [mercado.id, casa.id].sort()]);
});

test("o desfazer diz qual parte da compra ficou como está e qual foi apagada", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/busca");
  await entrar(page);
  const api = await apiDaPagina(page);
  const { conta, mercado, casa } = await preparar(api, s);
  const parte = (descricao: string, valor_centavos: number) => ({ id: randomUUID(), descricao, valor_centavos, categoria_ids: [mercado.id], tags: [] });
  const compra = await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 10000,
    data: "2026-03-02",
    descricao: `Loja ${s}`,
    conta_id: conta.id,
    categoria_ids: [],
    tags: [],
    partes: [parte("Vassoura", 5000), parte("Arroz", 3000), parte("Sabão", 2000)],
  });

  await buscar(page, s);
  await page.getByRole("button", { name: "Selecionar para editar em lote" }).click();
  await page.getByLabel(`Marcar Loja ${s}`).check();
  await page.getByRole("button", { name: "Editar em lote" }).click();
  const folha = page.getByRole("dialog", { name: "Editar em lote" });
  await folha.getByRole("group", { name: "Categorias de despesa" }).getByRole("button", { name: `Casa ${s}` }).click();
  await folha.getByRole("button", { name: "Ver prévia" }).click();
  await folha.getByRole("button", { name: "Aplicar em 1 lançamento" }).click();
  await expect(folha).toBeHidden();

  // Depois do lote: o arroz vai só para a Casa e o sabão sai da compra.
  const [agora] = (await api.ler("/api/lancamentos")).filter((l: { id: string }) => l.id === compra.id);
  const [vassoura, arroz] = agora.partes;
  await api.mudar(`/api/lancamentos/${compra.id}`, {
    versao: agora.versao,
    partes: [{ ...vassoura, valor_centavos: 7000 }, { ...arroz, categoria_ids: [casa.id] }],
  });

  await page.getByRole("status").getByRole("link", { name: "Desfazer" }).click();
  await page.getByRole("button", { name: `Desfazer Categorias: acrescentar Casa ${s}` }).click();

  const status = page.getByRole("status");
  await expect(status).toContainText(`Desfeita: Categorias: acrescentar Casa ${s}, em 1 lançamento.`);
  const pulados = status.getByRole("list", { name: "Pulados no desfazer" }).getByRole("listitem");
  await expect(pulados).toHaveCount(2);
  await expect(pulados.first()).toContainText(`Loja ${s} › Arroz: você mudou as categorias ou as tags depois`);
  await expect(pulados.last()).toHaveText(`Loja ${s} › parte apagada por você`);
  const [desfeita] = (await api.ler("/api/lancamentos")).filter((l: { id: string }) => l.id === compra.id);
  expect(desfeita.partes.map((p: { categoria_ids: string[] }) => p.categoria_ids)).toEqual([[mercado.id], [casa.id]]);
});
