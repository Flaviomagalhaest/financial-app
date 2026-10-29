import { expect, test, type Browser, type Page } from "@playwright/test";
import { entrar } from "./entrar";
import { cadastrar, digitar, lancar } from "./lancar";

test.use({ timezoneId: "America/Sao_Paulo" });

// Os dois do casal, cada um no seu contexto (o seu "celular"), mexendo no mesmo lançamento.

const aba = (page: Page, nome: string) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome }).click();
const linha = (page: Page, texto: string) => page.getByRole("listitem").filter({ hasText: texto });

/** Flávio cadastra conta e categoria e lança "Mercado <s>" de R$ 1,00; a esposa entra no outro celular. */
async function prepararCasal(page: Page, browser: Browser) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, mercado, descricao] = [`Corrente ${s}`, `Mercado ${s}`, `Mercado ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  await lancar(page, { teclas: ["1", "00"], conta, categoria: mercado, descricao });
  await expect(linha(page, descricao)).not.toContainText("não enviado");

  const contextoDela = await browser.newContext();
  const dela = await contextoDela.newPage();
  await dela.goto("/#/historico");
  await entrar(dela, "esposa@teste.com");
  await expect(linha(dela, descricao)).toContainText("R$ 1,00");
  return { s, descricao, dela, contextoDela };
}

/** Abre a edição pela lista e acrescenta uma tecla ao valor (R$ 1,00 + "7" = R$ 10,07). */
async function editarValor(page: Page, descricao: string, tecla: string) {
  await linha(page, descricao).getByRole("link", { name: `Editar ${descricao}` }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 1,00");
  await page.getByRole("button", { name: tecla, exact: true }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
}

test("mudanças em campos diferentes do mesmo lançamento ficam as duas", async ({ page, context, browser }) => {
  const { s, descricao, dela, contextoDela } = await prepararCasal(page, browser);

  await context.setOffline(true);
  await editarValor(page, descricao, "7");
  await expect(linha(page, descricao)).toContainText("⏳ não enviado");

  await linha(dela, descricao).getByRole("link", { name: `Editar ${descricao}` }).click();
  await dela.getByText("Detalhes").click();
  await dela.getByLabel("Descrição").fill(`Feira ${s}`);
  await dela.getByRole("button", { name: "Salvar" }).click();
  await expect(linha(dela, `Feira ${s}`)).not.toContainText("não enviado");

  await context.setOffline(false);
  const juntos = linha(page, `Feira ${s}`);
  await expect(juntos).toContainText("− R$ 10,07");
  await expect(juntos).not.toContainText("não enviado");
  await expect(juntos).not.toContainText("conflito");
  await dela.reload();
  await expect(linha(dela, `Feira ${s}`)).toContainText("− R$ 10,07");
  await contextoDela.close();
});

test("mudança no mesmo campo vira conflito: o aparelho mostra a versão do servidor e decide campo a campo", async ({ page, context, browser }) => {
  const { descricao, dela, contextoDela } = await prepararCasal(page, browser);

  await context.setOffline(true);
  await editarValor(page, descricao, "7");
  await editarValor(dela, descricao, "5");
  await expect(linha(dela, descricao)).toContainText("− R$ 10,05");
  await context.setOffline(false);

  const minha = linha(page, descricao);
  await expect(minha).toContainText("⚠ conflito: sua mudança espera decisão");
  // Enquanto espera, os dois celulares mostram o mesmo número.
  await expect(minha).toContainText("− R$ 10,05");
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("1 lançamento com conflito: decida no Histórico.");

  await aba(page, "Histórico");
  await minha.getByRole("link", { name: `Decidir ${descricao}` }).click();
  const valor = page.getByRole("group", { name: "Valor" });
  await expect(valor.getByRole("button", { name: "O seu: R$ 10,07" })).toBeVisible();
  await expect(valor.getByRole("button", { name: /^O de Fulana, às \d\d:\d\d: R\$ 10,05$/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Salvar a decisão" })).toBeDisabled();
  await valor.getByRole("button", { name: "O seu: R$ 10,07" }).click();
  await page.getByRole("button", { name: "Salvar a decisão" }).click();

  await expect(minha).toContainText("− R$ 10,07");
  await expect(minha).not.toContainText("conflito");
  await expect(minha).not.toContainText("não enviado");
  await dela.reload();
  await expect(linha(dela, descricao)).toContainText("− R$ 10,07");
  await contextoDela.close();
});

test("descartar a minha mudança deixa a versão da outra pessoa", async ({ page, context, browser }) => {
  const { descricao, dela, contextoDela } = await prepararCasal(page, browser);

  await context.setOffline(true);
  await editarValor(page, descricao, "7");
  await editarValor(dela, descricao, "5");
  await context.setOffline(false);
  await linha(page, descricao).getByRole("link", { name: `Decidir ${descricao}` }).click();
  await page.getByRole("button", { name: "Descartar a minha mudança" }).click();

  await expect(linha(page, descricao)).toContainText("− R$ 10,05");
  await expect(linha(page, descricao)).not.toContainText("conflito");
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  await contextoDela.close();
});

test("a exclusão vence a edição, com aviso e 'Lançar de novo'", async ({ page, context, browser }) => {
  const { descricao, dela, contextoDela } = await prepararCasal(page, browser);

  await context.setOffline(true);
  await editarValor(page, descricao, "7");
  dela.once("dialog", (dialogo) => void dialogo.accept());
  await linha(dela, descricao).getByRole("button", { name: `Excluir ${descricao}` }).click();
  await expect(linha(dela, descricao)).toHaveCount(0);
  await context.setOffline(false);

  const minha = linha(page, descricao);
  await expect(minha).toContainText("Fulana excluiu este lançamento; sua alteração não foi salva.");
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("1 excluído pela outra pessoa");
  await aba(page, "Histórico");
  await minha.getByRole("button", { name: `Lançar de novo ${descricao}` }).click();

  await expect(minha).toContainText("− R$ 10,07");
  await expect(minha).not.toContainText("excluiu");
  await expect(minha).not.toContainText("não enviado");
  await dela.reload();
  await expect(linha(dela, descricao)).toContainText("− R$ 10,07");
  await contextoDela.close();
});

test("excluir o que a outra pessoa mudou depois pergunta antes", async ({ page, context, browser }) => {
  const { descricao, dela, contextoDela } = await prepararCasal(page, browser);

  await context.setOffline(true);
  await editarValor(dela, descricao, "5");
  page.once("dialog", (dialogo) => void dialogo.accept());
  await linha(page, descricao).getByRole("button", { name: `Excluir ${descricao}` }).click();
  await expect(linha(page, descricao)).toHaveCount(0);
  await context.setOffline(false);

  const minha = linha(page, descricao);
  await expect(minha).toContainText("⚠ conflito");
  await expect(minha).toContainText("− R$ 10,05");
  await minha.getByRole("link", { name: `Decidir ${descricao}` }).click();
  await expect(page.getByText("Fulana alterou este lançamento depois da versão que você excluiu: valor.")).toBeVisible();
  await page.getByRole("button", { name: "Excluir mesmo assim" }).click();

  await expect(minha).toHaveCount(0);
  await dela.reload();
  await expect(linha(dela, descricao)).toHaveCount(0);
  await contextoDela.close();
});

test("confirmar com ajuste o que a outra pessoa já confirmou leva à tela de conflito", async ({ page, browser }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, luz, descricao] = [`Corrente ${s}`, `Luz ${s}`, `Conta de luz ${s}`];
  const amanha = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(Date.now() + 86_400_000));
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", luz, "despesa");
  await page.getByRole("link", { name: "Hoje" }).first().click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, "1", "00");
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: luz }).click();
  await page.getByText("Detalhes").click();
  await page.getByLabel("Descrição").fill(descricao);
  await page.getByLabel("Data").fill(amanha);
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(linha(page, descricao)).toContainText("previsto");
  await aba(page, "Hoje");
  await expect(linha(page, descricao)).toBeVisible();

  const contextoDela = await browser.newContext({ timezoneId: "America/Sao_Paulo" });
  const dela = await contextoDela.newPage();
  await dela.goto("/#/hoje");
  await entrar(dela, "esposa@teste.com");
  await linha(dela, descricao).getByRole("button", { name: `Confirmar ${descricao}` }).click();
  await expect(linha(dela, descricao)).toHaveCount(0);

  // A tela dele ainda mostra o previsto: ele ajusta o valor e confirma.
  await linha(page, descricao).getByRole("button", { name: `Ajustar ${descricao}` }).click();
  await page.getByRole("button", { name: "7", exact: true }).click();
  await page.getByRole("button", { name: "Confirmar com ajuste" }).click();

  const valor = page.getByRole("group", { name: "Valor" });
  await expect(valor.getByRole("button", { name: /^O de Fulana, às \d\d:\d\d: R\$ 1,00$/ })).toBeVisible();
  await valor.getByRole("button", { name: "O seu: R$ 10,07" }).click();
  await page.getByRole("button", { name: "Salvar a decisão" }).click();

  const minha = linha(page, descricao);
  await expect(minha).toContainText("− R$ 10,07");
  await expect(minha).not.toContainText("previsto");
  await expect(minha).not.toContainText("conflito");
  await dela.goto("/#/historico");
  await expect(linha(dela, descricao)).toContainText("− R$ 10,07");
  await contextoDela.close();
});
