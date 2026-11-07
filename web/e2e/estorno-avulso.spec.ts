import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { digitar } from "./lancar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

/** Dia `deslocamento` dias a partir de hoje em São Paulo, como `AAAA-MM-DD`. */
function dia(deslocamento: number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(Date.now() + deslocamento * 86_400_000));
}

/** `2026-11-01` vira `11/2026`. */
const mesDaFatura = (iso: string) => `${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** O valor de uma linha do resumo da fatura (`dt` e `dd` lado a lado). */
const resumo = (page: Page, nome: string) =>
  page.getByLabel("Resumo da fatura").locator("dt", { hasText: new RegExp(`^${nome}$`) }).locator("xpath=following-sibling::dd[1]");

/** Entra e prepara pela API um cartão, uma categoria e uma compra de R$ 100,00 hoje. */
async function prepararFatura(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [cartaoNome, categoriaNome, compraNome] = [`Visa ${s}`, `Vestuário ${s}`, `Tênis ${s}`];
  await page.goto("/#/historico");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  const api = await apiDaPagina(page);
  const cartao = await api.criar("/api/cartoes", { nome: cartaoNome, dia_fechamento: 10, dia_vencimento: 20 });
  const categoria = await api.criar("/api/categorias", { nome: categoriaNome, tipo: "despesa" });
  const compra = await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 10000,
    data: dia(0),
    descricao: compraNome,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
  });
  await page.goto(`/#/cartoes/${cartao.id}/${compra.mes}`);
  await expect(resumo(page, "Total")).toHaveText("R$ 100,00");
  return { s, api, cartao, categoria, compra, cartaoNome, categoriaNome };
}

test("lança um crédito na tela da fatura sem categoria: diminui a fatura, aparece como estorno avulso e se edita", async ({ page }) => {
  const { s, cartao, compra, cartaoNome } = await prepararFatura(page);
  const nome = `Centavos ${s}`;

  await page.getByRole("link", { name: "Lançar crédito" }).click();
  await expect(page.getByRole("heading", { name: "Lançar crédito", level: 2 })).toBeVisible();
  // Abre no cartão da fatura, sem tipo nem conta para escolher, e a categoria é opcional.
  await expect(page.getByRole("button", { name: cartaoNome })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: "Receita" })).toHaveCount(0);
  await expect(page.getByText(`Entra na fatura de ${mesDaFatura(compra.mes)}`)).toBeVisible();
  await expect(page.getByRole("button", { name: "Salvar" })).toBeDisabled();
  await digitar(page, "3", "7");
  await expect(page.getByTestId("valor")).toHaveText("R$ 0,37");
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(nome);
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();

  const credito = page.getByRole("listitem").filter({ hasText: nome });
  await expect(credito).toContainText("+ R$ 0,37");
  await expect(credito).toContainText("estorno avulso");
  // O total da fatura vem do servidor: espera a fila enviar antes de abri-la.
  await expect(credito).not.toContainText("não enviado");
  await page.goto(`/#/cartoes/${cartao.id}/${compra.mes}`);
  await expect(resumo(page, "Estornos")).toHaveText("− R$ 0,37");
  await expect(resumo(page, "Total")).toHaveText("R$ 99,63");
  await expect(page.getByRole("listitem").filter({ hasText: nome })).toContainText("+ R$ 0,37");

  // Editar o crédito: o valor muda, e ele não vira receita nem sai do cartão.
  await page.goto("/#/historico");
  await page.getByRole("link", { name: `Editar ${nome}` }).click();
  await expect(page.getByRole("heading", { name: "Editar crédito", level: 2 })).toBeVisible();
  await page.getByRole("button", { name: "Apagar" }).click();
  await digitar(page, "5");
  await expect(page.getByTestId("valor")).toHaveText("R$ 0,35");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: nome })).toContainText("+ R$ 0,35");
  await expect(page.getByRole("listitem").filter({ hasText: nome })).not.toContainText("não enviado");
  await page.goto(`/#/cartoes/${cartao.id}/${compra.mes}`);
  await expect(resumo(page, "Total")).toHaveText("R$ 99,65");
});

test("o crédito com categoria entra na fila sem internet e sobe quando a rede volta, e o Repetir último não o oferece", async ({ page, context }) => {
  const { s, api, cartao, compra, categoriaNome } = await prepararFatura(page);
  const nome = `Crédito ${s}`;

  await context.setOffline(true);
  await page.getByRole("link", { name: "Lançar crédito" }).click();
  await digitar(page, "2", "5", "0", "0");
  await page.getByRole("button", { name: categoriaNome }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(nome);
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  const credito = page.getByRole("listitem").filter({ hasText: nome });
  await expect(credito).toContainText("+ R$ 25,00");
  await expect(credito).toContainText(categoriaNome);
  await expect(credito).toContainText("⏳ não enviado");

  // O crédito não serve de modelo para o "Repetir último" do lançamento novo.
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await expect(page.getByRole("button", { name: /^Repetir último/ })).toHaveCount(0);
  await page.goto("/#/historico");

  await context.setOffline(false);
  await expect(credito).not.toContainText("não enviado");
  const gravados = (await api.ler("/api/lancamentos")) as { descricao: string; estorno_avulso: boolean; valor_centavos: number; categoria_ids: string[] }[];
  expect(gravados.find((l) => l.descricao === nome)).toMatchObject({ estorno_avulso: true, valor_centavos: 2500 });
  const fatura = (await api.ler(`/api/cartoes/${cartao.id}/faturas`)).find((f: { mes: string }) => f.mes === compra.mes);
  expect(fatura).toMatchObject({ total_centavos: 7500 });
});

/**
 * Entra e prepara pela API um cartão que fecha no dia 28, duas categorias com item no planejamento do mês e uma compra
 * de R$ 100,00 no dia 1 (a fatura do mês, que a fatura fecha depois): o crédito avulso tem devido de onde sair (ticket 189).
 */
async function prepararPlanejamento(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const mes = dia(0).slice(0, 7);
  await page.goto("/#/historico");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  const api = await apiDaPagina(page);
  const cartao = await api.criar("/api/cartoes", { nome: `Visa ${s}`, dia_fechamento: 28, dia_vencimento: 5 });
  const mercado = await api.criar("/api/categorias", { nome: `Mercado ${s}`, tipo: "despesa" });
  const lazer = await api.criar("/api/categorias", { nome: `Lazer ${s}`, tipo: "despesa" });
  for (const c of [mercado, lazer]) await api.criar(`/api/planejamento/${mes}/itens`, { id: randomUUID(), categoria_id: c.id, valor_centavos: 100000 });
  await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 10000,
    data: `${mes}-01`,
    descricao: `Compra ${s}`,
    conta_id: cartao.id,
    categoria_ids: [mercado.id],
  });
  return { s, mes, api, cartao, mercado, lazer };
}

test("o crédito com duas categorias com item pergunta o item, e a escolha vai para o servidor", async ({ page }) => {
  const { s, mes, api, cartao, mercado, lazer } = await prepararPlanejamento(page);
  const nome = `Crédito ${s}`;

  await page.goto(`/#/cartoes/${cartao.id}/${mes}-01`);
  await page.getByRole("link", { name: "Lançar crédito" }).click();
  await digitar(page, "2", "0", "0", "0");
  await page.getByRole("button", { name: mercado.nome, exact: true }).click();
  await page.getByRole("button", { name: lazer.nome, exact: true }).click();
  const aviso = page.getByRole("region", { name: "Aviso de planejamento" });
  await expect(aviso.getByRole("heading", { name: "Conta no planejamento em:" })).toBeVisible();
  await aviso.getByRole("button", { name: lazer.nome, exact: true }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(nome);
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();

  const credito = page.getByRole("listitem").filter({ hasText: nome });
  await expect(credito).toContainText("+ R$ 20,00");
  await expect(credito).not.toContainText("não enviado");
  const gravados = (await api.ler("/api/lancamentos")) as { descricao: string; item_categoria_id: string | null; estorno_avulso: boolean }[];
  expect(gravados.find((l) => l.descricao === nome)).toMatchObject({ estorno_avulso: true, item_categoria_id: lazer.id });
  const planejamento = await api.ler(`/api/planejamento/${mes}`);
  expect(planejamento.itens.find((i: { categoria_id: string }) => i.categoria_id === lazer.id)).toMatchObject({ realizado_centavos: -2000 });
});

test("o crédito sem escolha de item aparece em \"A escolher\" da Hoje com o sinal de crédito", async ({ page }) => {
  const { s, mes, api, cartao, mercado, lazer } = await prepararPlanejamento(page);
  await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 3000,
    data: `${mes}-01`,
    descricao: `Crédito ${s}`,
    conta_id: cartao.id,
    categoria_ids: [mercado.id, lazer.id],
    estorno_avulso: true,
  });

  await page.goto("/#/hoje");
  await page.reload();

  const aEscolher = page.getByRole("region", { name: "A escolher" });
  await expect(aEscolher.getByRole("listitem").filter({ hasText: new RegExp(`Crédito ${s}|${mercado.nome}`) })).toContainText("+ R$ 30,00");
});

test("o crédito leva a tag e a pessoa escolhidas na tela", async ({ page }) => {
  const { s, api, cartao, mes } = await prepararPlanejamento(page);
  const nome = `Crédito ${s}`;
  const tag = `loja${s}`;

  await page.goto(`/#/cartoes/${cartao.id}/${mes}-01`);
  await page.getByRole("link", { name: "Lançar crédito" }).click();
  await digitar(page, "5", "0", "0");
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(nome);
  await page.getByPlaceholder("Nova tag").fill(tag);
  await page.getByRole("button", { name: "Criar tag" }).click();
  await page.getByRole("group", { name: "Pessoa" }).getByRole("button", { name: "Fulana" }).click();
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();

  const credito = page.getByRole("listitem").filter({ hasText: nome });
  await expect(credito).toContainText(`#${tag}`);
  await expect(credito).not.toContainText("não enviado");
  const gravados = (await api.ler("/api/lancamentos")) as { descricao: string; tags: string[]; pessoa: string | null; estorno_avulso: boolean }[];
  expect(gravados.find((l) => l.descricao === nome)).toMatchObject({ estorno_avulso: true, tags: [tag], pessoa: expect.any(String) });
  expect(gravados.find((l) => l.descricao === nome)?.pessoa).not.toBeNull();
});

test("\"Lançar crédito\" aparece no mês sem fatura criada", async ({ page }) => {
  const { cartao } = await prepararPlanejamento(page);

  await page.goto(`/#/cartoes/${cartao.id}/2031-01-01`);

  await expect(page.getByRole("link", { name: "Lançar crédito" })).toBeVisible();
  await expect(page.getByLabel("Resumo da fatura")).toHaveCount(0);
});
