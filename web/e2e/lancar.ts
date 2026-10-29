import { expect, type Page } from "@playwright/test";

export async function digitar(page: Page, ...teclas: string[]) {
  for (const tecla of teclas) await page.getByRole("button", { name: tecla, exact: true }).click();
}

export async function cadastrar(page: Page, formulario: string, nome: string, tipo: string) {
  const form = page.getByRole("form", { name: formulario });
  await form.getByLabel("Nome").fill(nome);
  await form.getByLabel("Tipo").selectOption(tipo);
  await form.getByRole("button", { name: "Cadastrar" }).click();
  await expect(page.getByRole("listitem").filter({ hasText: nome })).toBeVisible();
}

/** Abre o novo lançamento pelo app (sem recarregar, para funcionar sem internet) e salva. */
export async function lancar(page: Page, { teclas, conta, categoria, descricao, pessoa }: { teclas: string[]; conta: string; categoria: string; descricao: string; pessoa?: string }) {
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, ...teclas);
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: categoria }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  if (pessoa) await page.getByRole("group", { name: "Pessoa" }).getByRole("button", { name: pessoa }).click();
  await page.getByLabel("Descrição").fill(descricao);
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
}
