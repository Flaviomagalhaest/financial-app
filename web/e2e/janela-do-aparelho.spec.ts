import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { esperarFilaVazia, filaDoAparelho } from "./fila";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

const hoje = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());

/** 10 de março de `anos` anos atrás: fora da janela do aparelho, que tem 12 meses (ADR 0025). */
const haAnos = (anos: number) => `${Number(hoje().slice(0, 4)) - anos}-03-10`;

const aba = (page: Page, nome: string) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome }).click();

/** Uma conta, um cartão e uma categoria, criados pela API, e o Histórico aberto com a janela guardada. */
async function preparar(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/historico");
  await entrar(page);
  const api = await apiDaPagina(page);
  const conta = await api.criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const cartao = await api.criar("/api/cartoes", { nome: `Visa ${s}`, dia_fechamento: 10, dia_vencimento: 20 });
  const categoria = await api.criar("/api/categorias", { nome: `Mercado ${s}`, tipo: "despesa" });
  const lancar = (descricao: string, data: string, contaId = conta.id, valor_centavos = 4500) =>
    api.criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos, data, descricao: `${descricao} ${s}`, conta_id: contaId, categoria_ids: [categoria.id] });
  return { s, api, conta, cartao, lancar };
}

/** Abre uma tela pelo endereço sem recarregar: sem internet, recarregar não abre o app. */
const abrir = (page: Page, hash: string) => page.evaluate((h) => (location.hash = h), hash);

test("o lançamento fora da janela não fica no aparelho: com internet abre do servidor e se edita, sem internet a tela diz que não está aqui", async ({ page, context }) => {
  const { s, api, lancar } = await preparar(page);
  const antigo = await lancar("Geladeira", haAnos(2));
  await lancar("Padaria", hoje());
  await page.reload();
  await expect(page.getByRole("listitem").filter({ hasText: `Padaria ${s}` })).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: `Geladeira ${s}` })).toHaveCount(0);

  await abrir(page, `#/novo/${antigo.id}`);
  await expect(page.getByTestId("valor")).toHaveText("R$ 45,00");

  await context.setOffline(true);
  await abrir(page, "#/historico");
  await abrir(page, `#/novo/${antigo.id}`);
  await expect(page.getByText("Sem internet: este lançamento não está no aparelho.")).toBeVisible();

  // A rede voltou: a tela lê o lançamento do servidor e se edita.
  await context.setOffline(false);
  await abrir(page, "#/historico");
  await abrir(page, `#/novo/${antigo.id}`);
  await expect(page.getByTestId("valor")).toHaveText("R$ 45,00");
  await page.getByRole("button", { name: "0", exact: true }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect.poll(async () => (await api.ler(`/api/lancamentos/${antigo.id}`)).lancamento.valor_centavos).toBe(45000);
  // Enviada a edição, ele continua fora da janela: o Histórico não o mostra.
  await expect(page.getByRole("listitem").filter({ hasText: `Padaria ${s}` })).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: `Geladeira ${s}` })).toHaveCount(0);
});

test("o estorno de uma compra fora da janela lê a compra do servidor e, sem internet, pede internet", async ({ page, context }) => {
  const { s, cartao, lancar } = await preparar(page);
  const compra = await lancar("Sofá", haAnos(2), cartao.id, 60000);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  await abrir(page, `#/estornar/${compra.id}`);
  await expect(page.getByTestId("valor")).toHaveText("R$ 600,00");
  await expect(page.getByText(`Estorno Sofá ${s}`)).toBeVisible();

  await context.setOffline(true);
  await abrir(page, "#/historico");
  await abrir(page, `#/estornar/${compra.id}`);
  await expect(page.getByText("Sem internet: esta compra não está no aparelho.")).toBeVisible();
  await context.setOffline(false);
});

test("a busca sem internet olha só a janela e diz isso; com internet acha o lançamento antigo", async ({ page, context }) => {
  const { s, lancar } = await preparar(page);
  await lancar("Geladeira", haAnos(2));
  await page.reload();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  await context.setOffline(true);
  await page.getByRole("link", { name: "Buscar lançamentos" }).click();
  await page.getByRole("searchbox", { name: "Buscar" }).fill(`Geladeira ${s}`);
  await expect(page.getByRole("status")).toHaveText("Sem internet: a busca olhou só os últimos 12 meses.");
  await expect(page.getByRole("listitem").filter({ hasText: `Geladeira ${s}` })).toHaveCount(0);

  await context.setOffline(false);
  await expect(page.getByRole("listitem").filter({ hasText: `Geladeira ${s}` })).toBeVisible();
  await expect(page.getByRole("status")).toHaveCount(0);
});

test("quando o mês vira, o que saiu da janela some do aparelho, menos o que tem mudança não enviada", async ({ page, context }) => {
  const { s, api, lancar } = await preparar(page);
  const editado = await lancar("Feira", hoje());
  await lancar("Farmácia", hoje());
  await page.reload();
  const feira = page.getByRole("listitem").filter({ hasText: `Feira ${s}` });
  const farmacia = page.getByRole("listitem").filter({ hasText: `Farmácia ${s}` });
  await expect(feira).toBeVisible();
  await expect(farmacia).toBeVisible();

  await context.setOffline(true);
  await feira.getByRole("link", { name: `Editar Feira ${s}` }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 45,00");
  await page.getByRole("button", { name: "0", exact: true }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(feira).toContainText("⏳ não enviado");

  // O mês virou: a janela do servidor não traz mais os dois. O envio fica preso, e a edição segue na fila.
  await page.route((url) => url.pathname === "/api/lancamentos", (rota) => (rota.request().method() === "GET" ? rota.fulfill({ json: [] }) : rota.fallback()));
  await page.route("**/api/lancamentos/lote", (rota) => rota.abort("connectionreset"));
  const releitura = page.waitForResponse((r) => new URL(r.url()).pathname === "/api/lancamentos" && r.request().method() === "GET");
  await context.setOffline(false);
  await releitura;
  await aba(page, "Hoje");
  await aba(page, "Histórico");
  await expect(farmacia).toHaveCount(0);
  await expect(feira).toContainText("− R$ 450,00");
  await expect(feira).toContainText("⏳ não enviado");

  // O envio sobe a edição sobre a versão guardada, sem conflito, e o lançamento sai do aparelho na leitura seguinte.
  await page.unroute("**/api/lancamentos/lote");
  await aba(page, "Hoje");
  // Com a rota solta, a fila pode subir sozinha e levar o botão antes do clique; se não, "Enviar agora" sobe.
  await expect(async () => {
    const enviar = page.getByRole("button", { name: "Enviar agora" });
    if ((await enviar.count()) > 0) await enviar.click({ timeout: 2_000 }).catch(() => {});
    expect(await filaDoAparelho(page)).toEqual([]);
  }).toPass();
  await esperarFilaVazia(page);
  expect((await api.ler(`/api/lancamentos/${editado.id}`)).lancamento.valor_centavos).toBe(45000);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Hoje", level: 2 })).toBeVisible();
  await aba(page, "Histórico");
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect(feira).toHaveCount(0);
});

test("a edição sem resposta de uma parcela fora da janela aparece editada, com o que só o servidor tinha (o número dela), e não como um lançamento novo", async ({ page }) => {
  const { s, api, cartao } = await preparar(page);
  const categoria = await api.criar("/api/categorias", { nome: `Casa ${s}`, tipo: "despesa" });
  const parcelamento = await api.criar("/api/parcelamentos", {
    id: randomUUID(),
    valor_total_centavos: 30000,
    parcelas: 3,
    descricao: `Geladeira ${s}`,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
    data: haAnos(2),
  });
  const [primeira] = (await api.ler(`/api/parcelamentos/${parcelamento.id}/lancamentos`)) as { id: string; data: string }[];
  await page.reload();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  await page.route("**/api/lancamentos/lote", (rota) => rota.abort("connectionreset"));
  await abrir(page, `#/novo/${primeira.id}`);
  await expect(page.getByTestId("valor")).toHaveText("R$ 100,00");
  await page.getByRole("button", { name: "0", exact: true }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await page.getByRole("group", { name: "Mudar quais parcelas?" }).getByRole("button", { name: "Só esta" }).click();

  const linha = page.getByRole("listitem").filter({ hasText: `Geladeira ${s}` });
  await expect(linha).toHaveCount(1);
  await expect(linha).toContainText("01/03");
  await expect(linha).toContainText("− R$ 1.000,00");
  await expect(linha).toContainText("⏳ não enviado");

  await page.unroute("**/api/lancamentos/lote");
  await aba(page, "Hoje");
  // Com a rota solta, a fila pode subir sozinha e levar o botão antes do clique; se não, "Enviar agora" sobe.
  await expect(async () => {
    const enviar = page.getByRole("button", { name: "Enviar agora" });
    if ((await enviar.count()) > 0) await enviar.click({ timeout: 2_000 }).catch(() => {});
    expect(await filaDoAparelho(page)).toEqual([]);
  }).toPass();
  await esperarFilaVazia(page);
  const gravada = (await api.ler(`/api/lancamentos/${primeira.id}`)).lancamento;
  expect(gravada.valor_centavos).toBe(100000);
  expect(gravada.parcela).toBe(1);
  expect(gravada.data).toBe(primeira.data);
});

/** O dia 10 de `meses` meses atrás (a janela do aparelho começa 12 meses antes do mês de hoje, ADR 0025). */
const haMeses = (meses: number) => {
  const [ano, mes] = hoje().split("-").map(Number);
  const d = new Date(Date.UTC(ano, mes - 1 - meses, 10));
  return d.toISOString().slice(0, 10);
};

const mesDaFatura = (iso: string) => `${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

test("o estorno na fatura de hoje, de uma compra antiga fora da janela, mostra o nome da compra com internet (ticket 176)", async ({ page }) => {
  const { s, api, cartao, lancar } = await preparar(page);
  const compra = await lancar("Sofá", haAnos(2), cartao.id, 60000);
  const categoria = (await api.ler("/api/categorias")).find((c: { nome: string }) => c.nome === `Mercado ${s}`);
  const estorno = await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 20000,
    data: hoje(),
    descricao: `Devolução ${s}`,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
    estorno_de: compra.id,
  });
  await page.reload();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  await abrir(page, `#/cartoes/${cartao.id}/${estorno.mes}`);
  await expect(page.getByRole("heading", { name: `Fatura de ${mesDaFatura(estorno.mes)}`, level: 2 })).toBeVisible();
  const linha = page.getByRole("listitem").filter({ hasText: `Devolução ${s}` });
  await expect(linha).toContainText(`estorno de Sofá ${s}`);
});

test("o estorno de uma parcela na janela, com as outras parcelas e o estorno delas fora, deixa o restante igual ao do servidor (ticket 176)", async ({ page }) => {
  const { s, api, cartao } = await preparar(page);
  const categoria = await api.criar("/api/categorias", { nome: `Casa ${s}`, tipo: "despesa" });
  const parcelamento = await api.criar("/api/parcelamentos", {
    id: randomUUID(),
    valor_total_centavos: 40000,
    parcelas: 4,
    descricao: `Fogão ${s}`,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
    data: haMeses(14),
  });
  const parcelas = (await api.ler(`/api/parcelamentos/${parcelamento.id}/lancamentos`)) as { id: string; parcela: number }[];
  const ultima = parcelas.find((p) => p.parcela === 4)!;
  // O estorno de todas as parcelas é antigo: fora da janela, com as primeiras parcelas.
  await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 35000,
    data: haMeses(14),
    descricao: `Devolução ${s}`,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
    estorno_parcelamento_id: parcelamento.id,
  });
  await page.reload();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  await abrir(page, `#/estornar/${ultima.id}`);
  // Só R$ 50,00 do parcelamento ainda dá para estornar, e não os R$ 100,00 da parcela.
  await expect(page.getByTestId("valor")).toHaveText("R$ 50,00");
});

test("o mês que vira poupa o lançamento em conflito, como o da mudança não enviada (ticket 176)", async ({ page, context }) => {
  const { s, api, lancar } = await preparar(page);
  const conflitante = await lancar("Feira", hoje());
  await lancar("Farmácia", hoje());
  await page.reload();
  const feira = page.getByRole("listitem").filter({ hasText: `Feira ${s}` });
  const farmacia = page.getByRole("listitem").filter({ hasText: `Farmácia ${s}` });
  await expect(feira).toBeVisible();
  await expect(farmacia).toBeVisible();

  // Sem internet, edita a feira; enquanto isso, outro aparelho muda a mesma, e o envio dá conflito.
  await context.setOffline(true);
  await feira.getByRole("link", { name: `Editar Feira ${s}` }).click();
  await page.getByRole("button", { name: "0", exact: true }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(feira).toContainText("⏳ não enviado");
  const versao = (await api.ler(`/api/lancamentos/${conflitante.id}`)).lancamento.versao;
  await api.mudar(`/api/lancamentos/${conflitante.id}`, { valor_centavos: 7000, versao });

  await context.setOffline(false);
  await expect(feira).toContainText("⚠ conflito");

  // O mês virou: a janela do servidor não traz mais os dois, e o conflito continua no aparelho.
  await page.route((url) => url.pathname === "/api/lancamentos", (rota) => (rota.request().method() === "GET" ? rota.fulfill({ json: [] }) : rota.fallback()));
  const releitura = page.waitForResponse((r) => new URL(r.url()).pathname === "/api/lancamentos" && r.request().method() === "GET");
  await aba(page, "Hoje");
  await releitura;
  await aba(page, "Histórico");
  await expect(farmacia).toHaveCount(0);
  await expect(feira).toContainText("⚠ conflito");
});
