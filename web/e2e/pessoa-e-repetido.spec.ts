import { expect, test, type Browser, type Page } from "@playwright/test";
import { entrar } from "./entrar";
import { cadastrar, lancar } from "./lancar";

test.use({ timezoneId: "America/Sao_Paulo" });

// Pessoa, autoria e "Parece repetido" com os dois do casal, cada um no seu contexto (o seu "celular").

const linha = (page: Page, texto: string) => page.getByRole("listitem").filter({ hasText: texto });

/** Flávio cadastra conta e categoria; a esposa entra no outro celular. */
async function prepararCasal(page: Page, browser: Browser) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, categoria] = [`Corrente ${s}`, `Mercado ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", categoria, "despesa");
  const contextoDela = await browser.newContext({ timezoneId: "America/Sao_Paulo" });
  const dela = await contextoDela.newPage();
  await dela.goto("/#/historico");
  await entrar(dela, "esposa@teste.com");
  return { s, conta, categoria, dela, contextoDela };
}

test("a pessoa do lançamento aparece na lista dos dois e o menu Informações diz quem criou e a origem", async ({ page, browser }) => {
  const { s, conta, categoria, dela, contextoDela } = await prepararCasal(page, browser);
  const [dele, dodois] = [`Almoço ${s}`, `Internet ${s}`];

  await lancar(page, { teclas: ["1", "00"], conta, categoria, descricao: dele, pessoa: "Flávio" });
  await lancar(page, { teclas: ["2", "00"], conta, categoria, descricao: dodois });
  await expect(linha(page, dodois)).not.toContainText("não enviado");
  await dela.reload();
  await expect(linha(page, dele)).toContainText("Flávio");
  await expect(linha(page, dodois)).toContainText("conjunto");
  await expect(linha(dela, dele)).toContainText("Flávio");
  await expect(linha(dela, dodois)).toContainText("conjunto");

  await linha(dela, dele).getByText("⋯").click();
  await linha(dela, dele).getByRole("button", { name: `Informações ${dele}` }).click();
  const informacoes = dela.getByRole("definition");
  await expect(informacoes.nth(0)).toHaveText(/^Flávio, às \d\d:\d\d$/);
  await expect(informacoes.nth(1)).toHaveText(/^Flávio, às \d\d:\d\d$/);
  await expect(informacoes.nth(2)).toHaveText("app");
  await contextoDela.close();
});

test("a pessoa se troca na edição e a outra pessoa vê a troca", async ({ page, browser }) => {
  const { s, conta, categoria, dela, contextoDela } = await prepararCasal(page, browser);
  const descricao = `Cinema ${s}`;
  await lancar(page, { teclas: ["1", "00"], conta, categoria, descricao });
  await expect(linha(page, descricao)).not.toContainText("não enviado");
  await dela.reload();
  await expect(linha(dela, descricao)).toContainText("conjunto");

  await linha(dela, descricao).getByRole("link", { name: `Editar ${descricao}` }).click();
  await dela.getByRole("button", { name: /^Detalhes/ }).click();
  await dela.getByRole("group", { name: "Pessoa" }).getByRole("button", { name: "Fulana" }).click();
  await dela.getByRole("button", { name: "Pronto" }).click();
  await dela.getByRole("button", { name: "Salvar" }).click();
  await expect(linha(dela, descricao)).toContainText("Fulana");
  await expect(linha(dela, descricao)).not.toContainText("não enviado");
  await page.reload();
  await expect(linha(page, descricao)).toContainText("Fulana");
  await contextoDela.close();
});

test("'Parece repetido' aparece só para quem recebeu o lançamento igual, e 'Manter os dois' o tira", async ({ page, browser }) => {
  const { s, conta, categoria, dela, contextoDela } = await prepararCasal(page, browser);
  const descricao = `Mercado ${s}`;

  await lancar(page, { teclas: ["8", "00"], conta, categoria, descricao });
  await expect(linha(page, descricao)).not.toContainText("não enviado");
  await lancar(dela, { teclas: ["8", "00"], conta, categoria, descricao });
  await expect(linha(dela, descricao).first()).not.toContainText("não enviado");
  await expect(dela.getByRole("group", { name: `Parece repetido ${descricao}` })).toHaveCount(0);

  // O "não enviado" que sumiu pode ser o dele: o dela chega ao servidor quando a fila dela subir.
  await expect(async () => {
    await page.reload();
    await expect(linha(page, descricao)).toHaveCount(2, { timeout: 2000 });
  }).toPass();
  const repetido = page.getByRole("group", { name: `Parece repetido ${descricao}` });
  await expect(repetido).toContainText("Parece repetido: Fulana lançou o mesmo valor na mesma conta.");

  await repetido.getByRole("button", { name: `Manter os dois ${descricao}` }).click();
  await expect(repetido).toHaveCount(0);
  await page.reload();
  await expect(linha(page, descricao)).toHaveCount(2);
  await expect(page.getByRole("group", { name: `Parece repetido ${descricao}` })).toHaveCount(0);
  await contextoDela.close();
});

test("'Excluir este' tira o lançamento repetido para os dois", async ({ page, browser }) => {
  const { s, conta, categoria, dela, contextoDela } = await prepararCasal(page, browser);
  const descricao = `Padaria ${s}`;

  await lancar(page, { teclas: ["8", "00"], conta, categoria, descricao });
  await expect(linha(page, descricao)).not.toContainText("não enviado");
  await lancar(dela, { teclas: ["8", "00"], conta, categoria, descricao });
  await expect(linha(dela, descricao).first()).not.toContainText("não enviado");

  await expect(async () => {
    await page.reload();
    await expect(page.getByRole("group", { name: `Parece repetido ${descricao}` })).toBeVisible({ timeout: 2000 });
  }).toPass();
  page.once("dialog", (dialogo) => void dialogo.accept());
  await page.getByRole("group", { name: `Parece repetido ${descricao}` }).getByRole("button", { name: `Excluir este ${descricao}` }).click();

  await expect(linha(page, descricao)).toHaveCount(1);
  await expect(page.getByRole("group", { name: `Parece repetido ${descricao}` })).toHaveCount(0);
  // A exclusão sobe pela fila dele: a tela dela só a vê depois que ela chega ao servidor (ticket 114).
  await expect(async () => {
    await dela.reload();
    await expect(linha(dela, descricao)).toHaveCount(1, { timeout: 2000 });
  }).toPass();
  await contextoDela.close();
});
