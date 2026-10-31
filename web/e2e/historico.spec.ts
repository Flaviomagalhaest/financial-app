import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";

test.use({ timezoneId: "America/Sao_Paulo" });

const reais = (centavos: number) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(centavos / 100).replace(/\s/g, " ");

test("a aba Histórico mostra uma categoria em 12 meses contra os 12 anteriores, por ano e no mesmo mês de cada ano", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [ano, mes] = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date()).split("-").map(Number);
  const mm = String(mes).padStart(2, "0");
  await page.goto("/#/historico");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  // O banco do teste é dividido com os outros: a categoria nova deixa os totais só com o que ele lança.
  const { criar } = await apiDaPagina(page);
  const conta = await criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const categoria = await criar("/api/categorias", { nome: `Evolução ${s}`, tipo: "despesa" });
  const lancar = (centavos: number, data: string) =>
    criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos: centavos, data, descricao: "", conta_id: conta.id, categoria_ids: [categoria.id], tags: [] });
  await lancar(30000, `${ano}-${mm}-01`);
  await lancar(10000, `${ano - 1}-${mm}-01`);
  await lancar(5000, "2019-02-01");

  await page.reload();
  const evolucao = page.getByRole("region", { name: "Evolução" });
  await evolucao.getByRole("combobox", { name: "Métrica" }).selectOption("categoria");
  await evolucao.getByRole("combobox", { name: "Categoria", exact: true }).selectOption({ label: `Evolução ${s}` });

  // 12 meses: o mês atual é o último; o total e o mesmo mês um ano antes aparecem.
  await expect(evolucao.getByText("nos últimos 12 meses")).toContainText(reais(30000));
  const atual = evolucao.getByRole("listitem").last();
  await expect(atual).toContainText(reais(30000));
  await expect(atual).toContainText(`um ano antes: ${reais(10000)}`);

  await evolucao.getByRole("button", { name: "Por ano" }).click();
  await expect(evolucao.getByRole("listitem").filter({ hasText: /^2019/ })).toContainText(reais(5000));
  await expect(evolucao.getByRole("listitem").filter({ hasText: `${ano} (até agora)` })).toContainText(reais(30000));

  await evolucao.getByRole("button", { name: "Mesmo mês" }).click();
  await expect(evolucao.getByRole("listitem").filter({ hasText: `de ${ano - 1}` })).toContainText(reais(10000));
  await evolucao.getByRole("combobox", { name: "Mês", exact: true }).selectOption("2");
  await expect(evolucao.getByRole("listitem").filter({ hasText: "fevereiro de 2019" })).toContainText(reais(5000));
});
