import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";
import { cadastrar, digitar, lancar } from "./lancar";

/** Abre o novo lançamento pelo app, digita o valor e escreve a descrição na folha de detalhes. */
async function descrever(page: Page, teclas: string[], descricao: string) {
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, ...teclas);
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(descricao);
  return page.getByRole("list", { name: "Sugestões" }).getByRole("button");
}

test("sugere pelo histórico sem internet: escolher preenche o pacote e mantém o valor, e o pacote corrigido vem primeiro", async ({ page, context }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, outraConta, mercado, casa] = [`Corrente ${s}`, `Carteira ${s}`, `Mercado ${s}`, `Casa ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova conta", outraConta, "carteira");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  await cadastrar(page, "Nova categoria", casa, "despesa");
  await lancar(page, { teclas: ["3", "00"], conta: outraConta, categoria: mercado, descricao: `Sacolão São ${s} (1/3)`, pessoa: "Flávio" });
  await expect(page.getByRole("listitem").filter({ hasText: `Sacolão São ${s}` })).not.toContainText("não enviado");

  await context.setOffline(true);
  // Uma letra ainda não sugere; sem acento, em maiúsculas e sem a parcela, a descrição é a mesma.
  const sugestoes = await descrever(page, ["4", "5", "00"], "s");
  await expect(sugestoes).toHaveCount(0);
  await page.getByLabel("Descrição").fill(`SACOLAO SAO ${s}`);
  await expect(sugestoes).toHaveCount(1);
  await expect(sugestoes.first()).toContainText(`${mercado} · ${outraConta} · Flávio`);
  // A palavra do meio que começa com o que se digitou também casa.
  await page.getByLabel("Descrição").fill(`${s}`);
  await expect(sugestoes).toHaveCount(1);

  await sugestoes.first().click();
  await expect(sugestoes).toHaveCount(0);
  await page.getByRole("button", { name: "Pronto" }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 45,00");
  await expect(page.getByRole("button", { name: outraConta })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: mercado })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: /^Detalhes/ })).toContainText("Flávio");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("listitem").filter({ hasText: "R$ 45,00" }).filter({ hasText: s })).toContainText("⏳ não enviado");

  // Corrigir as categorias, mesmo sem internet, põe esse pacote como o mais recente.
  await lancar(page, { teclas: ["7", "00"], conta, categoria: casa, descricao: `Sacolão São ${s}` });
  await descrever(page, ["1", "00"], `sacolão são ${s}`);
  await expect(sugestoes).toHaveCount(2);
  await expect(sugestoes.nth(0)).toContainText(`${casa} · ${conta} · Conjunto`);
  await expect(sugestoes.nth(1)).toContainText(`${mercado} · ${outraConta} · Flávio`);
});
