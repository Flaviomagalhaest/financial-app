import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { digitar } from "./lancar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

const dia = (deslocamento: number) => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(Date.now() + deslocamento * 86_400_000));
const sufixo = () => `${Date.now()}${Math.floor(Math.random() * 1000)}`;

/** Entra e monta, pela API, uma conta e uma categoria de despesa. */
async function prepararCasal(page: Page, s: string) {
  await page.goto("/#/hoje");
  await entrar(page);
  const api = await apiDaPagina(page);
  const conta = await api.criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const categoria = await api.criar("/api/categorias", { nome: `Café ${s}`, tipo: "despesa" });
  await page.reload();
  return { api, conta, categoria };
}

const naHoje = (page: Page) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();

/** Abre o novo lançamento pelo app, digita o valor e escolhe a conta e a categoria. */
async function novoComValor(page: Page, s: string, teclas: string[], descricao: string) {
  await naHoje(page);
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, ...teclas);
  await page.getByRole("button", { name: `Corrente ${s}` }).click();
  await page.getByRole("button", { name: `Café ${s}` }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(descricao);
  await page.getByRole("button", { name: "Pronto" }).click();
}

test("marcar pela ⭐ cria o favorito na fileira e na grade, e lança sem internet com o valor do último lançamento", async ({ page, context }) => {
  const s = sufixo();
  await prepararCasal(page, s);
  await novoComValor(page, s, ["1", "2", "00"], `Padaria ${s}`);
  await page.getByRole("button", { name: "☆ Marcar como favorito" }).click();
  await expect(page.getByRole("button", { name: "⭐ Será favorito" })).toBeVisible();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  // A grade da Hoje traz o favorito com o valor do lançamento.
  await naHoje(page);
  const grade = page.getByRole("region", { name: "Favoritos" });
  await expect(grade.getByRole("link", { name: new RegExp(`Padaria ${s}`) })).toContainText("R$ 12,00");
  // O app já guardou os favoritos para lançar sem internet.
  await page.reload();
  await expect(grade.getByRole("link", { name: new RegExp(`Padaria ${s}`) })).toBeVisible();

  await context.setOffline(true);
  // A fileira acima do teclado: tocar preenche tudo e o valor é só o padrão, editável.
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await page.getByRole("group", { name: "Favoritos" }).getByRole("button", { name: new RegExp(`Padaria ${s}`) }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 12,00");
  await expect(page.getByRole("button", { name: `Corrente ${s}` })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: `Café ${s}` })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: /^Detalhes/ })).toContainText(`Padaria ${s}`);
  // Já é favorito, e favoritar precisa de internet.
  await expect(page.getByRole("button", { name: "⭐ É favorito" })).toBeDisabled();
  for (let i = 0; i < 4; i++) await digitar(page, "Apagar");
  await digitar(page, "1", "3", "00");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("listitem").filter({ hasText: `Padaria ${s}` }).filter({ hasText: "R$ 13,00" })).toContainText("⏳ não enviado");

  // O valor padrão passa a ser o do último lançamento, mesmo o que ainda não subiu.
  await naHoje(page);
  await expect(grade.getByRole("link", { name: new RegExp(`Padaria ${s}`) })).toContainText("R$ 13,00");
  await page.getByRole("link", { name: new RegExp(`Padaria ${s}`) }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 13,00");

  // Com a rede de volta, a fila sobe e o servidor chega ao mesmo valor padrão.
  await context.setOffline(false);
  await naHoje(page);
  await expect(page.getByTestId("atrasados")).toHaveCount(0);
  await expect.poll(async () => (await page.request.get("/api/saude")).ok()).toBe(true);
  await page.reload();
  await expect(grade.getByRole("link", { name: new RegExp(`Padaria ${s}`) })).toContainText("R$ 13,00");
});

test("depois de salvar, o app oferece Favoritar; sem internet não oferece", async ({ page, context }) => {
  const s = sufixo();
  await prepararCasal(page, s);
  await novoComValor(page, s, ["8", "00"], `Lanche ${s}`);
  await page.getByRole("button", { name: "Salvar" }).click();
  const oferta = page.getByRole("status").filter({ hasText: "Salvo." });
  await oferta.getByRole("button", { name: "⭐ Favoritar" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Favorito criado" })).toBeVisible();
  await naHoje(page);
  await expect(page.getByRole("region", { name: "Favoritos" }).getByRole("link", { name: new RegExp(`Lanche ${s}`) })).toContainText("R$ 8,00");

  // Sem internet, favoritar é impossível: nada a oferecer, e a ⭐ avisa por quê.
  await context.setOffline(true);
  await novoComValor(page, s, ["9", "00"], `Outro lanche ${s}`);
  await expect(page.getByRole("button", { name: "☆ Marcar como favorito" })).toBeDisabled();
  await expect(page.getByText("Favoritar precisa de internet.")).toBeVisible();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "Salvo." })).toHaveCount(0);
});

test("os mais repetidos viram sugeridos; promover ou dispensar, e reordenar e remover nas configurações só com internet", async ({ page, context }) => {
  const s = sufixo();
  const { api, conta, categoria } = await prepararCasal(page, s);
  const repetir = async (vezes: number, descricao: string, centavos: number) => {
    for (let i = 0; i < vezes; i++) {
      await api.criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos: centavos, data: dia(-1), descricao, conta_id: conta.id, categoria_ids: [categoria.id] });
    }
  };
  // Quatro usos não bastam; sete e seis, sim.
  await repetir(4, `Quase ${s}`, 500);
  await repetir(7, `Mercado ${s}`, 2000);
  await repetir(6, `Feira ${s}`, 3000);

  await page.reload();
  const sugeridos = page.getByRole("region", { name: "Sugeridos" });
  await expect(sugeridos.getByRole("listitem").filter({ hasText: `Mercado ${s}` })).toContainText("7 usos");
  await expect(sugeridos.getByRole("listitem").filter({ hasText: `Feira ${s}` })).toContainText("6 usos");
  await expect(sugeridos).not.toContainText(`Quase ${s}`);

  // A ⭐ promove o sugerido; "Dispensar" o tira da lista.
  await sugeridos.getByRole("button", { name: `Favoritar Mercado ${s}` }).click();
  await expect(page.getByRole("region", { name: "Favoritos" }).getByRole("link", { name: new RegExp(`Mercado ${s}`) })).toContainText("R$ 20,00");
  await sugeridos.getByRole("button", { name: `Dispensar Feira ${s}` }).click();
  await expect(sugeridos.getByRole("listitem").filter({ hasText: `Feira ${s}` })).toHaveCount(0);

  // Reordenar e remover ficam nas configurações.
  await api.criar("/api/favoritos", { id: randomUUID(), descricao: `Padaria ${s}`, tipo: "despesa", conta_id: conta.id, categoria_ids: [categoria.id], tags: [], pessoa: null, valor_centavos: 1200 });
  await page.getByRole("link", { name: "Configurações" }).click();
  await page.getByRole("link", { name: "Favoritos" }).click();
  const lista = page.getByRole("list", { name: "Favoritos" }).getByRole("listitem");
  await expect(lista.filter({ hasText: `Padaria ${s}` })).toBeVisible();
  const ordem = () => lista.evaluateAll((itens) => itens.map((i) => i.querySelector("strong")?.textContent));
  const antes = await ordem();
  expect(antes.slice(-2)).toEqual([`Mercado ${s}`, `Padaria ${s}`]);
  await page.getByRole("button", { name: `Subir Padaria ${s}` }).click();
  await expect.poll(async () => (await ordem()).slice(-2)).toEqual([`Padaria ${s}`, `Mercado ${s}`]);

  // Sem internet, o cadastro dos favoritos fica desligado.
  await context.setOffline(true);
  await expect(page.getByRole("button", { name: `Remover Mercado ${s}` })).toBeDisabled();
  await expect(page.getByRole("button", { name: `Subir Mercado ${s}` })).toBeDisabled();
  await expect(page.getByText("Reordenar e remover precisam de internet.")).toBeVisible();
  await context.setOffline(false);

  await page.getByRole("button", { name: `Remover Padaria ${s}` }).click();
  await expect(lista.filter({ hasText: `Padaria ${s}` })).toHaveCount(0);
  await expect(lista.filter({ hasText: `Mercado ${s}` })).toBeVisible();
});
