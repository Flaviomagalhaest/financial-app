import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";

test.use({ timezoneId: "America/Sao_Paulo" });

const sufixo = () => `${Date.now()}${Math.floor(Math.random() * 1000)}`;

test("salvar uma busca, aplicá-la de novo, renomear e excluir", async ({ page }) => {
  const s = sufixo();
  await page.goto("/#/hoje");
  await entrar(page);
  const api = await apiDaPagina(page);
  const conta = await api.criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const mercado = await api.criar("/api/categorias", { nome: `Mercado ${s}`, tipo: "despesa" });
  await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 4500,
    data: new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date()),
    descricao: `Feira ${s}`,
    conta_id: conta.id,
    categoria_ids: [mercado.id],
    tags: [],
  });
  await page.goto("/#/busca");

  await page.getByLabel("Buscar na descrição").fill(`Feira ${s}`);
  // O texto entra nos critérios 300 ms depois de parar de digitar, e o endereço acompanha.
  await expect.poll(() => page.url()).toContain("texto=");
  await expect(page.getByRole("list", { name: "Resultado da busca" }).getByText(`Feira ${s}`)).toBeVisible();
  await page.getByRole("button", { name: "Salvar esta busca" }).click();
  await page.getByLabel("Nome do filtro").fill(`Feiras ${s}`);
  await page.getByLabel("Período do filtro").selectOption("este_mes");
  await page.getByRole("button", { name: "Salvar", exact: true }).click();
  const salvos = page.getByRole("list", { name: "Filtros salvos" });
  await expect(salvos.getByRole("button", { name: `Feiras ${s}`, exact: true })).toBeVisible();

  // Outra busca; o filtro salvo traz o texto de volta.
  await page.getByLabel("Buscar na descrição").fill("nada disso");
  await expect(page.getByText("Nenhum lançamento com esses critérios.")).toBeVisible();
  await salvos.getByRole("button", { name: `Feiras ${s}`, exact: true }).click();
  await expect(page.getByLabel("Buscar na descrição")).toHaveValue(`Feira ${s}`);
  await expect(page.getByRole("list", { name: "Resultado da busca" }).getByText(`Feira ${s}`)).toBeVisible();

  await page.getByRole("button", { name: `Gerenciar o filtro Feiras ${s}` }).click();
  await page.getByLabel("Novo nome do filtro").fill(`Compras ${s}`);
  await page.getByRole("button", { name: "Renomear" }).click();
  await expect(salvos.getByRole("button", { name: `Compras ${s}`, exact: true })).toBeVisible();

  await page.getByRole("button", { name: `Gerenciar o filtro Compras ${s}` }).click();
  await page.getByRole("button", { name: "Excluir" }).click();
  await expect(salvos.getByRole("button", { name: `Compras ${s}`, exact: true })).toHaveCount(0);
});
