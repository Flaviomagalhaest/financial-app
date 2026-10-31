import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { cadastrar, digitar } from "./lancar";

/** Entra e cadastra uma conta e uma categoria de despesa, guardadas no aparelho. */
async function prepararCasal(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, eletro] = [`Corrente ${s}`, `Eletro ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", eletro, "despesa");
  return { s, conta, eletro };
}

const aba = (page: Page, nome: string) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome }).click();

/** Abre o novo lançamento pelo app, preenche valor, conta, categoria e descrição e marca "Parcelado". */
async function comecarParcelado(page: Page, { teclas, conta, categoria, descricao }: { teclas: string[]; conta: string; categoria: string; descricao: string }) {
  await aba(page, "Hoje");
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, ...teclas);
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: categoria }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(descricao);
  await page.getByRole("group", { name: "Repete?" }).getByRole("button", { name: "Parcelado" }).click();
}

test("lança parcelado no cartão pela folha de detalhes e o servidor gera as parcelas", async ({ page }) => {
  const { s, eletro } = await prepararCasal(page);
  const visa = `Visa ${s}`;
  const api = await apiDaPagina(page);
  await api.criar("/api/cartoes", { nome: visa, dia_fechamento: 10, dia_vencimento: 20 });
  await page.reload();

  await comecarParcelado(page, { teclas: ["1", "00", "00"], conta: visa, categoria: eletro, descricao: `Geladeira ${s}` });
  await page.getByLabel("Parcelas").fill("3");
  // O total de R$ 100,00 em 3: os centavos que sobram vão na 1ª.
  await expect(page.getByRole("dialog").getByText("3x: R$ 33,34 na 1ª e R$ 33,33 nas outras")).toBeVisible();
  // No cartão o parcelamento já é automático, e a data é a da compra; situação e fatura são da regra.
  await expect(page.getByLabel(/^Automático/)).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Data da compra" })).toBeVisible();
  await expect(page.getByRole("group", { name: "Situação" })).toHaveCount(0);
  await expect(page.getByRole("group", { name: "Fatura" })).toHaveCount(0);
  await page.getByRole("button", { name: "Pronto" }).click();
  await expect(page.getByRole("button", { name: /^Detalhes/ })).toContainText("3x: R$ 33,34 na 1ª e R$ 33,33 nas outras");
  await page.getByRole("button", { name: "Salvar" }).click();

  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  const parcelas = page.getByRole("listitem").filter({ hasText: `Geladeira ${s}` });
  await expect(parcelas).toHaveCount(3);
  await expect(page.getByRole("region", { name: "Parcelamentos não enviados" })).toHaveCount(0);

  const [gravado] = (await api.ler("/api/parcelamentos")).filter((p: { descricao: string }) => p.descricao === `Geladeira ${s}`);
  expect(gravado).toMatchObject({ valor_total_centavos: 10000, parcelas: 3, automatico: true });
});

test("sem internet, o parcelamento fica na fila como um pedido só e sobe uma vez quando a rede volta", async ({ page, context }) => {
  const { s, conta, eletro } = await prepararCasal(page);

  await context.setOffline(true);
  // Com juros: o valor digitado é o da parcela, num boleto que vira realizado sozinho.
  await comecarParcelado(page, { teclas: ["9", "9", "9", "0"], conta, categoria: eletro, descricao: `Fogão ${s}` });
  await page.getByLabel("Parcelas").fill("10");
  await page.getByRole("group", { name: "O valor digitado é" }).getByRole("button", { name: "O da parcela" }).click();
  await expect(page.getByRole("dialog").getByText("10x de R$ 99,90, total R$ 999,00")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Primeira parcela" })).toBeVisible();
  await page.getByLabel(/^Automático/).check();
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();

  const naoEnviados = page.getByRole("region", { name: "Parcelamentos não enviados" });
  await expect(naoEnviados.getByRole("listitem")).toHaveCount(1);
  await expect(naoEnviados).toContainText(`Fogão ${s}, 10x, não enviado`);
  await expect(naoEnviados).toContainText("R$ 999,00");
  await expect(naoEnviados.getByRole("button", { name: `Descartar Fogão ${s}` })).toBeVisible();
  // As parcelas são do servidor: sem internet, ainda não existem no aparelho.
  await expect(page.getByRole("listitem").filter({ hasText: `Fogão ${s}` })).toHaveCount(1);
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("1 parcelamento não enviado");

  // O servidor grava o lote, mas a resposta não chega ao aparelho: reenviar não duplica.
  let perdidas = 0;
  await page.route("**/api/lancamentos/lote", async (rota) => {
    if (perdidas > 0) return rota.continue();
    perdidas++;
    await rota.fetch();
    await rota.abort("connectionreset");
  });
  await context.setOffline(false);
  await expect.poll(() => perdidas).toBe(1);
  await aba(page, "Histórico");
  await expect(naoEnviados).toContainText("talvez já esteja no servidor");
  await expect(naoEnviados.getByRole("button", { name: `Descartar Fogão ${s}` })).toHaveCount(0);
  await aba(page, "Hoje");
  await page.getByRole("button", { name: "Enviar agora" }).click();
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);

  await aba(page, "Histórico");
  await expect(naoEnviados).toHaveCount(0);
  await expect(page.getByRole("listitem").filter({ hasText: `Fogão ${s}` })).toHaveCount(10);
  const api = await apiDaPagina(page);
  const gravados = (await api.ler("/api/parcelamentos")).filter((p: { descricao: string }) => p.descricao === `Fogão ${s}`);
  expect(gravados).toHaveLength(1);
  expect(gravados[0]).toMatchObject({ valor_total_centavos: 99900, parcelas: 10, automatico: true });
});

test("parcelamento recusado fica 'não enviado: <motivo>' até ser descartado", async ({ page, context }) => {
  // O aparelho guardou uma conta que o servidor não tem mais (como um cartão arquivado depois).
  const sumida = `Conta sumida ${Date.now()}`;
  await page.route("**/api/contas", async (rota) => {
    if (rota.request().method() !== "GET") return rota.continue();
    const resposta = await rota.fetch();
    const contas = await resposta.json();
    await rota.fulfill({ response: resposta, json: [...contas, { id: crypto.randomUUID(), nome: sumida, tipo: "corrente" }] });
  });
  const { s, conta, eletro } = await prepararCasal(page);

  await context.setOffline(true);
  await comecarParcelado(page, { teclas: ["6", "00"], conta: sumida, categoria: eletro, descricao: `Sofá ${s}` });
  await page.getByLabel("Parcelas").fill("6");
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  // Um lançamento junto: o aviso conta os dois tipos de pedido.
  await aba(page, "Hoje");
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, "5");
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: eletro }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("1 lançamento e 1 parcelamento não enviados");
  await context.setOffline(false);

  await aba(page, "Histórico");
  const naoEnviados = page.getByRole("region", { name: "Parcelamentos não enviados" });
  await expect(naoEnviados).toContainText(`Sofá ${s}, 6x, não enviado: conta não encontrada`);
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("1 parcelamento não enviado (1 recusado");

  await aba(page, "Histórico");
  await naoEnviados.getByRole("button", { name: `Descartar Sofá ${s}` }).click();
  await expect(naoEnviados).toHaveCount(0);
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("parcelamentos longos sobem em lotes separados, para o servidor responder a tempo", async ({ page, context }) => {
  const { s, conta, eletro } = await prepararCasal(page);

  await context.setOffline(true);
  for (const descricao of [`Carro ${s}`, `Casa ${s}`]) {
    await comecarParcelado(page, { teclas: ["3", "00", "00", "00"], conta, categoria: eletro, descricao });
    await page.getByLabel("Parcelas").fill("300");
    await page.getByRole("button", { name: "Pronto" }).click();
    await page.getByRole("button", { name: "Salvar" }).click();
    await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  }
  // Só os lotes que o servidor respondeu: o envio do último salvar, sem rede, ainda pode sair agora.
  const lotes: number[] = [];
  page.on("requestfinished", (pedido) => {
    if (pedido.url().endsWith("/api/lancamentos/lote")) lotes.push(pedido.postDataJSON().acoes.length);
  });
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("2 parcelamentos não enviados");
  // A rede volta e a fila sobe sozinha.
  await context.setOffline(false);
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  // As 600 parcelas passam das 420 de um lote: cada parcelamento vai num.
  expect(lotes).toEqual([1, 1]);
});
