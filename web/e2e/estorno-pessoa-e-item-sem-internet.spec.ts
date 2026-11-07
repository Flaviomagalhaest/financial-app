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

test("a pessoa da compra mudada sem internet aparece no estorno ligado a ela (ticket 194)", async ({ page, context }) => {
  const { s, api, cartao, roupa } = await preparar(page);
  const compraNome = `Tênis ${s}`;
  const compra = await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 10000,
    data: hoje(),
    descricao: compraNome,
    conta_id: cartao.id,
    categoria_ids: [roupa.id],
  });
  await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 4000,
    data: hoje(),
    descricao: `Estorno ${compraNome}`,
    conta_id: cartao.id,
    categoria_ids: [roupa.id],
    estorno_de: compra.id,
  });
  await page.reload();
  await expect(page.getByRole("link", { name: `Editar Estorno ${compraNome}` })).toBeVisible();

  // Sem internet, a pessoa da compra muda para Flávio.
  await context.setOffline(true);
  await page.getByRole("link", { name: `Editar ${compraNome}`, exact: true }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByRole("group", { name: "Pessoa" }).getByRole("button", { name: "Flávio" }).click();
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  // O estorno ligado já mostra a pessoa da compra, sem edição.
  await page.getByRole("link", { name: `Editar Estorno ${compraNome}` }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  const pessoa = page.getByRole("group", { name: "Pessoa" });
  await expect(pessoa.getByRole("button", { name: "Flávio" })).toHaveAttribute("aria-pressed", "true");
  await expect(pessoa.getByRole("button", { name: "Conjunto" })).toBeDisabled();
});

test("o estorno de todas as parcelas sem partes leva o item do parcelamento sem internet (ticket 194)", async ({ page, context }) => {
  const { s, api, cartao, roupa, casa } = await preparar(page);
  const mes = hoje().slice(0, 7);
  for (const categoria of [roupa, casa]) await api.criar(`/api/planejamento/${mes}/itens`, { id: randomUUID(), categoria_id: categoria.id, valor_centavos: 100000 });
  const compra = `Loja ${s}`;
  const parcelamentoId = randomUUID();
  await api.criar("/api/parcelamentos", {
    id: parcelamentoId,
    parcelas: 3,
    data: hoje(),
    descricao: compra,
    conta_id: cartao.id,
    categoria_ids: [roupa.id, casa.id],
    item_categoria_id: casa.id,
    valor_total_centavos: 30000,
    automatico: true,
  });
  await page.reload();
  await expect(page.getByRole("link", { name: `Estornar ${compra}` }).first()).toBeVisible();

  await context.setOffline(true);
  await page.getByRole("listitem").filter({ hasText: compra }).first().getByRole("link", { name: `Estornar ${compra}` }).click();
  await page.getByRole("radio", { name: "Todas as parcelas" }).check();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  // O que sobe da fila leva a escolha de item do parcelamento.
  const envio = page.waitForRequest((r) => r.method() === "POST" && r.url().endsWith("/api/lancamentos/lote"));
  await context.setOffline(false);
  expect((await envio).postDataJSON().acoes[0].lancamento).toMatchObject({ estorno_parcelamento_id: parcelamentoId, item_categoria_id: casa.id });
});
