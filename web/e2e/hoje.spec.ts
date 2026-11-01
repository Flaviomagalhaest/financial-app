import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

/** Dia `deslocamento` dias a partir de hoje em São Paulo, como `AAAA-MM-DD`. */
function dia(deslocamento: number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(Date.now() + deslocamento * 86_400_000));
}

/** Ainda não há tela de planejamento nem de cartão: o teste monta o mês pela API, com o token da página. */
async function tokenDaPagina(page: Page): Promise<string> {
  const pedido = page.waitForRequest((r) => r.url().includes("/api/") && !!r.headers().authorization);
  await page.reload();
  return (await pedido).headers().authorization;
}

async function instalarCasca(page: Page) {
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
}

test("a Hoje junta ainda dá para gastar, a escolher, atrasados, fatura que vence e itens acima de 80%, e guarda a última leitura", async ({ page, context }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [restaurante, viagem, luz, visa] = [`Restaurante ${s}`, `Viagem ${s}`, `Luz ${s}`, `Visa ${s}`];
  await page.goto("/#/hoje");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Hoje", level: 2 })).toBeVisible();
  const headers = { authorization: await tokenDaPagina(page) };
  const enviar = async (caminho: string, data: object) => {
    const resposta = await page.request.post(caminho, { headers, data });
    expect(resposta.ok(), await resposta.text()).toBe(true);
    return resposta.json();
  };
  const mes = dia(0).slice(0, 7);
  const [catRestaurante, catViagem, catLuz] = await Promise.all([restaurante, viagem, luz].map((nome) => enviar("/api/categorias", { nome, tipo: "despesa" })));
  const conta = await enviar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  // Dia 1 do mês de hoje: sempre dentro do mês, nunca no futuro.
  const lancar = (categorias: { id: string }[], centavos: number, descricao: string, extra: object = {}) =>
    enviar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos: centavos, data: `${mes}-01`, descricao, conta_id: conta.id, categoria_ids: categorias.map((c) => c.id), ...extra });
  for (const [categoria, centavos] of [[catRestaurante, 100000], [catViagem, 300000], [catLuz, 100000]] as const) {
    await enviar(`/api/planejamento/${mes}/itens`, { id: randomUUID(), categoria_id: categoria.id, valor_centavos: centavos });
  }
  await lancar([catLuz], 85000, `Conta de luz ${s}`);
  await lancar([catRestaurante, catViagem], 4000, `Jantar ${s}`);
  await lancar([catLuz], 7000, `Boleto atrasado ${s}`, { data: dia(-2), situacao: "previsto" });
  const cartao = await enviar("/api/cartoes", { nome: visa, dia_fechamento: Number(dia(-5).slice(8)), dia_vencimento: Number(dia(2).slice(8)) });
  await lancar([catLuz], 2000, `Compra no cartão ${s}`, { conta_id: cartao.id, data: dia(-10) });
  // Nos primeiros dias do mês, o boleto atrasado (de 2 dias atrás) e a compra no cartão (na fatura que
  // fechou 5 dias atrás) caem no mês anterior e não contam no item da luz deste mês.
  const noMes = (d: string) => d.startsWith(mes);
  const luzNoMes = `${(85000 + (noMes(dia(-2)) ? 7000 : 0) + (noMes(dia(-5)) ? 2000 : 0)) / 1000}%`;

  await page.reload();
  // O destaque.
  await expect(page.getByTestId("ainda-da-para-gastar")).toHaveText(/R\$ \d/);
  await expect(page.getByRole("region", { name: "Ainda dá para gastar este mês" })).toContainText("planejados");

  // Itens acima de 80%: a luz, com o boleto atrasado previsto e a compra no cartão somando quando caem neste mês.
  const perto = page.getByRole("region", { name: "Itens em destaque" });
  await expect(perto.getByRole("listitem").filter({ hasText: luz })).toContainText(luzNoMes);
  await expect(perto).not.toContainText(restaurante);

  // Atrasados na mesma leitura das contas da semana.
  await expect(page.getByTestId("atrasados")).toContainText(/conta[s]? atrasada/);
  const semana = page.getByRole("region", { name: "Contas da semana" });
  await expect(semana.getByRole("listitem").filter({ hasText: `Boleto atrasado ${s}` })).toContainText("atrasado");

  // A escolher: o jantar conta em dois itens e o casal escolhe um.
  const aEscolher = page.getByRole("region", { name: "A escolher" });
  const jantar = aEscolher.getByRole("listitem").filter({ hasText: `Jantar ${s}` });
  await expect(jantar).toBeVisible();
  await jantar.getByRole("button", { name: viagem }).click();
  await expect(jantar).toHaveCount(0);

  // Fatura que vence: a deste cartão vence em dois dias.
  const fatura = page.getByRole("region", { name: "Fatura que vence" }).getByRole("listitem").filter({ hasText: visa });
  await expect(fatura).toContainText("R$ 20,00");
  await expect(fatura).toContainText(`vence em ${dia(2).split("-").reverse().join("/")}`);

  // Sem internet, a última leitura fica na tela com "atualizado às".
  await instalarCasca(page);
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByText(/Sem internet: atualizado às \d\d:\d\d/)).toBeVisible();
  await expect(perto.getByRole("listitem").filter({ hasText: luz })).toContainText(luzNoMes);
});
