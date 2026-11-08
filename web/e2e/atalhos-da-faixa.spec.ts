import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import { apiDaPagina } from "./api";
import { peloMenuDaConta } from "./conta";
import { entrar } from "./entrar";

const sufixo = () => `${Date.now()}${Math.floor(Math.random() * 1000)}`;

test("os favoritos viram pílulas na faixa da Hoje; desligar os atalhos em Configurações devolve a grade, e a escolha fica no aparelho", async ({ page }) => {
  const s = sufixo();
  await page.goto("/#/hoje");
  await entrar(page);
  const api = await apiDaPagina(page);
  const conta = await api.criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const categoria = await api.criar("/api/categorias", { nome: `Café ${s}`, tipo: "despesa" });
  await api.criar("/api/favoritos", { id: randomUUID(), descricao: `Lanche ${s}`, tipo: "despesa", conta_id: conta.id, categoria_ids: [categoria.id], tags: [], pessoa: null, valor_centavos: 800 });
  await page.reload();

  // Ligados (o padrão): o favorito é uma pílula com o valor, e a grade sai do corpo da Hoje.
  const atalhos = page.getByRole("list", { name: "Atalhos" });
  await expect(atalhos.getByRole("link", { name: new RegExp(`Lanche ${s}`) })).toContainText("R$ 8,00");
  await expect(atalhos.getByRole("link", { name: /Contas e categorias/ })).toContainText(/\d+ contas?/);
  await expect(page.getByRole("region", { name: "Favoritos" })).toHaveCount(0);
  // Tocar na pílula abre o lançamento preenchido pelo favorito.
  await atalhos.getByRole("link", { name: new RegExp(`Lanche ${s}`) }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 8,00");

  // Desligar em Configurações: a faixa fica sem atalhos e a grade volta.
  await peloMenuDaConta(page, "Configurações");
  const interruptor = page.getByRole("switch", { name: "Atalhos na faixa verde" });
  await expect(interruptor).toBeChecked();
  await interruptor.click();
  await expect(interruptor).not.toBeChecked();
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await expect(page.getByRole("region", { name: "Favoritos" }).getByRole("link", { name: new RegExp(`Lanche ${s}`) })).toContainText("R$ 8,00");
  await expect(atalhos).toHaveCount(0);

  // A escolha fica guardada neste aparelho.
  await page.reload();
  await expect(page.getByRole("region", { name: "Favoritos" }).getByRole("link", { name: new RegExp(`Lanche ${s}`) })).toBeVisible();
  await expect(atalhos).toHaveCount(0);
});
