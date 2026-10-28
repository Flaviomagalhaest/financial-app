import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";

const digitar = async (page: Page, ...teclas: string[]) => {
  for (const tecla of teclas) await page.getByRole("button", { name: tecla, exact: true }).click();
};

async function cadastrar(page: Page, formulario: string, nome: string, tipo: string) {
  const form = page.getByRole("form", { name: formulario });
  await form.getByLabel("Nome").fill(nome);
  await form.getByLabel("Tipo").selectOption(tipo);
  await form.getByRole("button", { name: "Cadastrar" }).click();
  await expect(page.getByRole("listitem").filter({ hasText: nome })).toBeVisible();
}

test("cria, edita e exclui um lançamento simples e o vê na lista", async ({ page }) => {
  const s = String(Date.now());
  const [conta, mercado, viagem, salario] = [`Corrente ${s}`, `Mercado ${s}`, `Viagem ${s}`, `Salário ${s}`];
  await page.goto("/#/cadastro");
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
  await page.getByText("Detalhes").click();
  await page.getByLabel("Descrição").fill(`Jantar ${s}`);
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
  await page.goto("/#/cadastro");
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
