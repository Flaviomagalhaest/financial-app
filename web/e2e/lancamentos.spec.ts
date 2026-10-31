import { expect, test } from "@playwright/test";
import { entrar } from "./entrar";
import { cadastrar, digitar } from "./lancar";

test("cria, edita e exclui um lançamento simples e o vê na lista", async ({ page }) => {
  const s = String(Date.now());
  const [conta, mercado, viagem, salario] = [`Corrente ${s}`, `Mercado ${s}`, `Viagem ${s}`, `Salário ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  await cadastrar(page, "Nova categoria", viagem, "despesa");
  await cadastrar(page, "Nova categoria", salario, "receita");

  // Teclado por centavos: os dígitos entram pela direita, `00` e apagar.
  await page.goto("/#/novo");
  const valor = page.getByTestId("valor");
  const salvar = page.getByRole("button", { name: "Salvar" });
  await expect(valor).toHaveText("R$ 0,00");
  await expect(salvar).toBeDisabled();
  await digitar(page, "1", "2", "0", "3", "5");
  await expect(valor).toHaveText("R$ 120,35");
  await digitar(page, "Apagar");
  await expect(valor).toHaveText("R$ 12,03");
  await digitar(page, "00");
  await expect(valor).toHaveText("R$ 1.203,00");
  await digitar(page, ...Array(6).fill("Apagar"));
  await digitar(page, "1", "2", "0", "3", "5");
  await expect(valor).toHaveText("R$ 120,35");

  // Salvar só com valor e ao menos uma categoria; receita mostra só categorias de receita.
  await expect(salvar).toBeDisabled();
  await expect(page.getByRole("button", { name: salario })).toHaveCount(0);
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: mercado }).click();
  await page.getByRole("button", { name: viagem }).click();
  await expect(salvar).toBeEnabled();
  await page.getByRole("button", { name: viagem }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(`Jantar ${s}`);
  await page.getByRole("button", { name: "Pronto" }).click();
  await salvar.click();

  const linha = page.getByRole("listitem").filter({ hasText: `Jantar ${s}` });
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect(linha).toContainText("− R$ 120,35");
  await expect(linha).toContainText(mercado);
  await expect(linha).toContainText(conta);

  // Edita pela lista: a tela abre preenchida.
  await linha.getByRole("link", { name: `Editar Jantar ${s}` }).click();
  await expect(page.getByRole("heading", { name: "Editar lançamento", level: 2 })).toBeVisible();
  await expect(valor).toHaveText("R$ 120,35");
  await digitar(page, "Apagar", "Apagar", "Apagar", "Apagar", "Apagar", "2", "3", "0", "00");
  await expect(valor).toHaveText("R$ 230,00");
  await page.getByRole("button", { name: viagem }).click();
  await salvar.click();
  await expect(linha).toContainText("− R$ 230,00");
  await expect(linha).toContainText(viagem);

  // A edição vale também depois de recarregar (veio do servidor, não da memória da tela).
  await page.reload();
  await expect(linha).toContainText("− R$ 230,00");

  // Exclui pela lista, com confirmação.
  page.once("dialog", (dialogo) => void dialogo.accept());
  await linha.getByRole("button", { name: `Excluir Jantar ${s}` }).click();
  await expect(linha).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect(linha).toHaveCount(0);
});

test("lança uma receita e a lista a mostra com sinal de mais", async ({ page }) => {
  const s = String(Date.now());
  const [conta, salario] = [`Poupança ${s}`, `Salário ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page, "esposa@teste.com");
  await cadastrar(page, "Nova conta", conta, "poupanca");
  await cadastrar(page, "Nova categoria", salario, "receita");

  await page.goto("/#/novo");
  await page.getByRole("button", { name: "Receita" }).click();
  await digitar(page, "5", "00", "00");
  await expect(page.getByTestId("valor")).toHaveText("R$ 500,00");
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: salario }).click();
  await page.getByRole("button", { name: "Salvar" }).click();

  const linha = page.getByRole("listitem").filter({ hasText: salario });
  await expect(linha).toContainText("+ R$ 500,00");
});

test("contas e categorias: cria, renomeia e arquiva categorias, e a arquivada sai das opções do lançamento", async ({ page }) => {
  const s = String(Date.now());
  const [conta, despesa, receita, transferencia, renomeada] = [`Conta ${s}`, `Mercado ${s}`, `Salário ${s}`, `Reserva ${s}`, `Feira ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", despesa, "despesa");
  await cadastrar(page, "Nova categoria", receita, "receita");
  await cadastrar(page, "Nova categoria", transferencia, "transferencia");

  // Renomeia: o nome novo vale também depois de recarregar.
  await page.getByRole("button", { name: `Renomear ${despesa}` }).click();
  await page.getByLabel(`Novo nome de ${despesa}`).fill(renomeada);
  await page.getByRole("button", { name: "Salvar nome" }).click();
  await expect(page.getByRole("listitem").filter({ hasText: renomeada })).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: despesa })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("listitem").filter({ hasText: renomeada })).toBeVisible();

  // Arquivada some do novo lançamento; desarquivada volta.
  await page.getByRole("button", { name: `Arquivar ${renomeada}` }).click();
  await expect(page.getByRole("button", { name: `Desarquivar ${renomeada}` })).toBeVisible();
  await page.goto("/#/novo");
  await expect(page.getByRole("button", { name: renomeada })).toHaveCount(0);
  await page.getByRole("button", { name: "Receita" }).click();
  await expect(page.getByRole("button", { name: receita })).toBeVisible();
  await page.goto("/#/contas-e-categorias");
  await page.getByRole("button", { name: `Desarquivar ${renomeada}` }).click();
  await expect(page.getByRole("button", { name: `Arquivar ${renomeada}`, exact: true })).toBeVisible();
  await page.goto("/#/novo");
  await expect(page.getByRole("button", { name: renomeada })).toBeVisible();
});

test("a tela provisória #/cadastro deixou de existir", async ({ page }) => {
  await page.goto("/#/cadastro");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Hoje", level: 2 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cadastro" })).toHaveCount(0);
});

test("contas: cria com saldo de abertura, renomeia e arquiva, e a arquivada sai das opções do lançamento", async ({ page }) => {
  const s = String(Date.now());
  const [conta, renomeada, categoria] = [`Carteira ${s}`, `Cofre ${s}`, `Mercado ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  const form = page.getByRole("form", { name: "Nova conta" });
  await form.getByLabel("Nome").fill(conta);
  await form.getByLabel("Tipo").selectOption("carteira");
  await form.getByLabel("Saldo de abertura").fill("1.234,56");
  await form.getByLabel("Data de abertura").fill("2020-01-01");
  await form.getByRole("button", { name: "Cadastrar" }).click();
  const linha = page.getByRole("listitem").filter({ hasText: conta });
  await expect(linha).toContainText("R$ 1.234,56");
  await cadastrar(page, "Nova categoria", categoria, "despesa");

  await page.getByRole("button", { name: `Editar ${conta}` }).click();
  await page.getByLabel(`Novo nome de ${conta}`).fill(renomeada);
  await page.getByRole("button", { name: "Salvar conta" }).click();
  const renomeadaLinha = page.getByRole("listitem").filter({ hasText: renomeada });
  await expect(renomeadaLinha).toContainText("R$ 1.234,56");

  await page.goto("/#/novo");
  await expect(page.getByRole("button", { name: renomeada })).toBeVisible();
  await page.goto("/#/contas-e-categorias");
  await page.getByRole("button", { name: `Arquivar conta ${renomeada}` }).click();
  await expect(page.getByRole("button", { name: `Desarquivar conta ${renomeada}` })).toBeVisible();
  await page.goto("/#/novo");
  await expect(page.getByRole("button", { name: renomeada })).toHaveCount(0);
});

test("a leitura das contas que saiu antes de arquivar e chega depois não desfaz o arquivar", async ({ page, context }) => {
  const conta = `Carteira ${Date.now()}`;
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "carteira");

  // A leitura que a tela faz ao abrir chega por último, como num banco cheio (ticket 120).
  let atrasar = true;
  let entregue = false;
  await page.route(
    (url) => url.pathname === "/api/contas" && url.search === "?arquivadas=true",
    async (rota) => {
      if (!atrasar) return rota.continue();
      atrasar = false;
      const resposta = await rota.fetch();
      await new Promise((pronto) => setTimeout(pronto, 1500));
      await rota.fulfill({ response: resposta });
      entregue = true;
    },
  );
  await page.goto("/#/novo");
  await page.goto("/#/contas-e-categorias");
  await page.getByRole("button", { name: `Arquivar conta ${conta}` }).click();
  const desarquivar = page.getByRole("button", { name: `Desarquivar conta ${conta}` });
  await expect(desarquivar).toBeVisible();
  await expect.poll(() => entregue).toBe(true);

  // Sem internet, a tela mostra o que ficou guardado.
  await context.setOffline(true);
  await page.goto("/#/novo");
  await page.goto("/#/contas-e-categorias");
  await expect(desarquivar).toBeVisible();
});
