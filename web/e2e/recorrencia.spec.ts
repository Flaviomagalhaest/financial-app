import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { cadastrar, digitar } from "./lancar";
import { diaEmSaoPaulo } from "../src/lancamentos/datas";

/** Entra e cadastra uma conta e uma categoria de despesa, guardadas no aparelho. */
async function prepararCasal(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, casa] = [`Corrente ${s}`, `Casa ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", casa, "despesa");
  return { s, conta, casa };
}

const aba = (page: Page, nome: string) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome }).click();

/** Abre o novo lançamento pelo app, preenche valor, conta, categoria e descrição e marca "Recorrente". */
async function comecarRecorrente(page: Page, { teclas, conta, categoria, descricao }: { teclas: string[]; conta: string; categoria: string; descricao: string }) {
  await aba(page, "Hoje");
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, ...teclas);
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: categoria }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(descricao);
  await page.getByRole("group", { name: "Repete?" }).getByRole("button", { name: "Recorrente" }).click();
}

test("lança recorrente pela folha de detalhes e o servidor gera os previstos", async ({ page }) => {
  const { s, conta, casa } = await prepararCasal(page);

  await comecarRecorrente(page, { teclas: ["5", "5", "00"], conta, categoria: casa, descricao: `Diarista ${s}` });
  // A cada 2 semanas, por 3 vezes, valor fixo e automático.
  await page.getByLabel("A cada").fill("2");
  await page.getByRole("group", { name: "Unidade" }).getByRole("button", { name: "Semanas" }).click();
  await page.getByRole("group", { name: "Termina" }).getByRole("button", { name: "Depois de" }).click();
  await page.getByLabel("Vezes").fill("3");
  await page.getByRole("group", { name: "Valor" }).getByRole("button", { name: "Fixo" }).click();
  await page.getByLabel(/^Automático/).check();
  // Situação e fatura são do lançamento único: a recorrência decide pela regra.
  await expect(page.getByRole("group", { name: "Situação" })).toHaveCount(0);
  await page.getByRole("button", { name: "Pronto" }).click();
  await expect(page.getByRole("button", { name: /^Detalhes/ })).toContainText("a cada 2 semanas, 3 vezes, automático");
  await page.getByRole("button", { name: "Salvar" }).click();

  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  const previstos = page.getByRole("listitem").filter({ hasText: `Diarista ${s}` });
  await expect(previstos).toHaveCount(3);
  await expect(previstos.first()).toContainText("− R$ 55,00");
  await expect(page.getByRole("region", { name: "Recorrências não enviadas" })).toHaveCount(0);

  const api = await apiDaPagina(page);
  const [regra] = (await api.ler("/api/recorrencias")).filter((r: { descricao: string }) => r.descricao === `Diarista ${s}`);
  expect(regra).toMatchObject({ valor_centavos: 5500, a_cada: 2, unidade: "semanas", vezes: 3, ate: null, tipo_do_valor: "fixo", automatico: true });
});

test("sem internet, a recorrência fica na fila como um pedido só e sobe uma vez quando a rede volta", async ({ page, context }) => {
  const { s, conta, casa } = await prepararCasal(page);

  await context.setOffline(true);
  await comecarRecorrente(page, { teclas: ["1", "8", "9", "9", "0"], conta, categoria: casa, descricao: `Luz ${s}` });
  // O padrão: todo mês, sem fim, valor estimado (sem "automático").
  await expect(page.getByLabel(/^Automático/)).toHaveCount(0);
  await page.getByRole("button", { name: "Pronto" }).click();
  await expect(page.getByRole("button", { name: /^Detalhes/ })).toContainText("todo mês");
  await page.getByRole("button", { name: "Salvar" }).click();

  const naoEnviadas = page.getByRole("region", { name: "Recorrências não enviadas" });
  await expect(naoEnviadas.getByRole("listitem")).toHaveCount(1);
  await expect(naoEnviadas).toContainText(`Luz ${s}, todo mês, não enviado`);
  await expect(naoEnviadas).toContainText("R$ 189,90");
  // Sem rede, o pedido nem saiu do aparelho: ainda dá para descartar.
  await expect(naoEnviadas.getByRole("button", { name: `Descartar Luz ${s}` })).toBeVisible();
  // Os previstos são do servidor: sem internet, ainda não existem no aparelho.
  await expect(page.getByRole("listitem").filter({ hasText: `Luz ${s}` })).toHaveCount(1);
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("1 recorrência não enviada");

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
  await expect(page.getByTestId("nao-enviados")).toContainText("1 recorrência não enviada");
  // Talvez já gravada: descartar no aparelho não tiraria os previstos do servidor.
  await aba(page, "Histórico");
  await expect(naoEnviadas).toContainText("talvez já esteja no servidor");
  await expect(naoEnviadas.getByRole("button", { name: `Descartar Luz ${s}` })).toHaveCount(0);
  await aba(page, "Hoje");
  await page.getByRole("button", { name: "Enviar agora" }).click();
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);

  await aba(page, "Histórico");
  await expect(naoEnviadas).toHaveCount(0);
  const previstos = page.getByRole("listitem").filter({ hasText: `Luz ${s}` });
  await expect(previstos.first()).toContainText("previsto");
  const api = await apiDaPagina(page);
  const regras = (await api.ler("/api/recorrencias")).filter((r: { descricao: string }) => r.descricao === `Luz ${s}`);
  expect(regras).toHaveLength(1);
  expect(regras[0]).toMatchObject({ valor_centavos: 18990, a_cada: 1, unidade: "meses", ate: null, vezes: null, tipo_do_valor: "estimado", automatico: false });
  // Todo mês até o horizonte de 24 meses, contando a de hoje.
  await expect(previstos).toHaveCount(25);
});

test("recorrência recusada fica 'não enviado: <motivo>' até ser descartada", async ({ page, context }) => {
  // O aparelho guardou uma conta que o servidor não tem mais (como um cartão arquivado depois).
  const sumida = `Conta sumida ${Date.now()}`;
  await page.route("**/api/contas", async (rota) => {
    if (rota.request().method() !== "GET") return rota.continue();
    const resposta = await rota.fetch();
    const contas = await resposta.json();
    await rota.fulfill({ response: resposta, json: [...contas, { id: crypto.randomUUID(), nome: sumida, tipo: "corrente" }] });
  });
  const { s, casa } = await prepararCasal(page);

  await context.setOffline(true);
  await comecarRecorrente(page, { teclas: ["3", "00"], conta: sumida, categoria: casa, descricao: `Seguro ${s}` });
  await page.getByLabel("A cada").fill("12");
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await context.setOffline(false);

  const naoEnviadas = page.getByRole("region", { name: "Recorrências não enviadas" });
  await expect(naoEnviadas).toContainText(`Seguro ${s}, todo ano, não enviado: conta não encontrada`);
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("1 recorrência não enviada (1 recusada");

  await aba(page, "Histórico");
  await naoEnviadas.getByRole("button", { name: `Descartar Seguro ${s}` }).click();
  await expect(naoEnviadas).toHaveCount(0);
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("lançada sem internet ontem e enviada hoje, a ocorrência de ontem chega realizada", async ({ page, context }) => {
  // O aparelho está no dia anterior ao do servidor; a fila só sobe depois que o dia vira.
  const [ano, mes, dia] = diaEmSaoPaulo(new Date()).split("-").map(Number);
  const ontem = new Date(Date.UTC(ano, mes - 1, dia - 1, 15)); // 12h em São Paulo
  await page.clock.install({ time: ontem });
  const { s, conta, casa } = await prepararCasal(page);

  await context.setOffline(true);
  await comecarRecorrente(page, { teclas: ["9", "00"], conta, categoria: casa, descricao: `Feira ${s}` });
  await page.getByRole("group", { name: "Termina" }).getByRole("button", { name: "Depois de" }).click();
  await page.getByLabel("Vezes").fill("2");
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("region", { name: "Recorrências não enviadas" })).toContainText(`Feira ${s}`);

  await page.clock.fastForward("24:00:00");
  await context.setOffline(false);
  await aba(page, "Hoje");
  await page.getByRole("button", { name: "Enviar agora" }).click();
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);

  const api = await apiDaPagina(page);
  const ontemIso = diaEmSaoPaulo(ontem);
  const [regra] = (await api.ler("/api/recorrencias")).filter((r: { descricao: string }) => r.descricao === `Feira ${s}`);
  expect(regra).toMatchObject({ inicio: ontemIso, dia_do_lancamento: ontemIso, vezes: 2 });
  const gerados = (await api.ler("/api/lancamentos"))
    .filter((l: { recorrencia_id: string }) => l.recorrencia_id === regra.id)
    .map((l: { data: string; situacao: string }) => [l.data, l.situacao])
    .sort();
  expect(gerados[0]).toEqual([ontemIso, "realizado"]);
  expect(gerados).toHaveLength(2);
});
