import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

const hoje = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());

/** Entra e prepara pela API um cartão e duas categorias de despesa. */
async function preparar(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/historico");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  const api = await apiDaPagina(page);
  const cartao = await api.criar("/api/cartoes", { nome: `Visa ${s}`, dia_fechamento: 10, dia_vencimento: 20 });
  const roupa = await api.criar("/api/categorias", { nome: `Roupa ${s}`, tipo: "despesa" });
  const casa = await api.criar("/api/categorias", { nome: `Casa ${s}`, tipo: "despesa" });
  return { s, api, cartao, roupa, casa };
}

test("estorna uma parte da compra: escolhe a parte, herda as categorias dela e vai até o valor dela", async ({ page }) => {
  const { s, api, cartao, roupa, casa } = await preparar(page);
  const compra = `Mercado Livre ${s}`;
  await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 10000,
    data: hoje(),
    descricao: compra,
    conta_id: cartao.id,
    categoria_ids: [],
    partes: [
      { id: randomUUID(), descricao: "Vestido", valor_centavos: 6000, categoria_ids: [roupa.id] },
      { id: randomUUID(), descricao: "Cortina", valor_centavos: 4000, categoria_ids: [casa.id] },
    ],
  });
  await page.reload();

  await page.getByRole("listitem").filter({ hasText: compra }).getByRole("link", { name: `Estornar ${compra}` }).click();

  // A primeira parte já vem escolhida, com o valor e as categorias dela.
  await expect(page.getByRole("heading", { name: "Estornar compra", level: 2 })).toBeVisible();
  const partes = page.getByRole("group", { name: "Parte estornada" });
  await expect(partes.getByRole("radio", { name: /^Vestido/ })).toBeChecked();
  await expect(page.getByTestId("valor")).toHaveText("R$ 60,00");
  await expect(page.getByRole("button", { name: roupa.nome })).toHaveAttribute("aria-pressed", "true");

  // Trocar de parte leva o valor e as categorias dela; a tela não deixa passar do valor da parte.
  await partes.getByRole("radio", { name: /^Cortina/ }).check();
  await expect(page.getByTestId("valor")).toHaveText("R$ 40,00");
  await expect(page.getByRole("button", { name: casa.nome })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: roupa.nome })).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByText(/ainda dá para estornar R\$ 40,00/)).toBeVisible();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  // O estorno diz de qual parte é, como crédito, e o servidor o ligou à parte.
  const estorno = page.getByRole("listitem").filter({ hasText: `estorno de ${compra} — Cortina` });
  await expect(estorno).toContainText("+ R$ 40,00");
  await expect(estorno).toContainText(casa.nome);
  const lidos = await api.ler("/api/lancamentos");
  const gravado = lidos.find((l: { estorno_parte_id?: string }) => l.estorno_parte_id);
  expect(gravado).toMatchObject({ valor_centavos: 4000, categoria_ids: [casa.id] });

  // A parte toda devolvida não se escolhe de novo; a outra, sim.
  await page.getByRole("listitem").filter({ hasText: compra }).filter({ hasText: "estornada em" }).getByRole("link", { name: `Estornar ${compra}` }).click();
  await expect(partes.getByRole("radio", { name: /^Cortina/ })).toBeDisabled();
  await expect(partes.getByRole("radio", { name: /^Vestido/ })).toBeChecked();
});

test("estorna todas as parcelas num estorno só, ligado ao parcelamento, que conta inteiro na fatura em que aparece", async ({ page }) => {
  const { s, api, cartao, roupa } = await preparar(page);
  const compra = `TV ${s}`;
  await api.criar("/api/parcelamentos", {
    id: randomUUID(),
    parcelas: 3,
    data: hoje(),
    descricao: compra,
    conta_id: cartao.id,
    categoria_ids: [roupa.id],
    tags: ["troca"],
    valor_total_centavos: 30000,
    automatico: true,
  });
  await page.reload();

  await page.getByRole("listitem").filter({ hasText: compra }).first().getByRole("link", { name: `Estornar ${compra}` }).click();
  await expect(page.getByRole("heading", { name: "Estornar compra", level: 2 })).toBeVisible();
  // "Só esta parcela" é o começo: R$ 100,00.
  await expect(page.getByRole("radio", { name: /^Só esta parcela/ })).toBeChecked();
  await expect(page.getByTestId("valor")).toHaveText("R$ 100,00");

  // "Todas": o valor passa a ser o restante do parcelamento.
  await page.getByRole("radio", { name: "Todas as parcelas" }).check();
  await expect(page.getByTestId("valor")).toHaveText("R$ 300,00");
  await expect(page.getByRole("button", { name: roupa.nome })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText(/Todas as parcelas de/)).toContainText("ainda dá para estornar até R$ 300,00");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  const estorno = page.getByRole("listitem").filter({ hasText: "estorno de todas as parcelas" });
  await expect(estorno).toContainText("+ R$ 300,00");
  const lidos = await api.ler("/api/lancamentos");
  const gravado = lidos.find((l: { estorno_parcelamento_id?: string }) => l.estorno_parcelamento_id);
  expect(gravado).toMatchObject({ valor_centavos: 30000, estorno_de: null, categoria_ids: [roupa.id], tags: ["troca"] });

  // Não sobra nada: nenhuma parcela oferece mais "Estornar".
  await expect(page.getByRole("link", { name: `Estornar ${compra}` })).toHaveCount(0);
});
