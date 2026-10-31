import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { apiDaPagina, tokenDaPagina } from "./api";
import { entrar } from "./entrar";
import { cadastrar, digitar } from "./lancar";

test.use({ timezoneId: "America/Sao_Paulo" });

const aba = (page: Page, nome: string) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome }).click();
/** Os lançamentos com esse texto, sem as mudanças não enviadas (que não mostram valor). */
const linha = (page: Page, texto: string) => page.getByRole("listitem").filter({ hasText: texto }).filter({ hasText: "R$" });
const historico = (page: Page) => expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

/** Daqui a `dias` dias em São Paulo (`AAAA-MM-DD`). */
const daquiA = (dias: number) => new Date(Date.now() + dias * 86_400_000).toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });

/** Cadastra conta e categoria pela tela e uma recorrência mensal "Luz <s>" de R$ 189,90 pela API, que começa daqui a 5 dias. */
async function prepararRegra(page: Page, vezes: number) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, casa, descricao] = [`Corrente ${s}`, `Casa ${s}`, `Luz ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", casa, "despesa");
  const api = await apiDaPagina(page);
  const contaId = (await api.ler("/api/contas")).find((c: { nome: string }) => c.nome === conta).id;
  const casaId = (await api.ler("/api/categorias")).find((c: { nome: string }) => c.nome === casa).id;
  const regra = await api.criar("/api/recorrencias", {
    id: crypto.randomUUID(),
    tipo: "despesa",
    valor_centavos: 18990,
    tipo_do_valor: "estimado",
    descricao,
    conta_id: contaId,
    categoria_ids: [casaId],
    inicio: daquiA(5),
    a_cada: 1,
    unidade: "meses",
    vezes,
  });
  // Abrir o Histórico com internet guarda os previstos e a regra no aparelho.
  await aba(page, "Histórico");
  await expect(linha(page, descricao)).toHaveCount(vezes);
  return { s, descricao, regra, api };
}

/** Pelo "⋯" de um lançamento da recorrência, abre a tela dela a partir dele. */
async function abrirRecorrencia(page: Page, lancamento: Locator, descricao: string) {
  await lancamento.getByLabel(`Mais ações ${descricao}`).click();
  await lancamento.getByRole("link", { name: `Recorrência ${descricao}` }).click();
  await expect(page.getByRole("heading", { name: "Recorrência", level: 2 })).toBeVisible();
}

async function mudarOValor(page: Page, valor: string) {
  await page.getByRole("textbox", { name: "Valor" }).fill(valor);
  await page.getByRole("button", { name: "Salvar daqui para frente" }).click();
  await historico(page);
}

test("muda daqui para frente, pula um mês e exclui a recorrência pela tela", async ({ page }) => {
  const { descricao, regra, api } = await prepararRegra(page, 3);
  // Do mais novo ao mais antigo: a 3ª, a 2ª e a 1ª vez.
  const previstos = linha(page, descricao);

  await abrirRecorrencia(page, previstos.nth(1), descricao);
  await expect(page.getByText("Esta vez:")).toContainText("previsto");
  await mudarOValor(page, "210,00");
  await expect(previstos.nth(0)).toContainText("− R$ 210,00");
  await expect(previstos.nth(1)).toContainText("− R$ 210,00");
  await expect(previstos.nth(2)).toContainText("− R$ 189,90");
  await expect(page.getByRole("region", { name: "Mudanças de recorrência não enviadas" })).toHaveCount(0);

  await abrirRecorrencia(page, previstos.nth(0), descricao);
  page.once("dialog", (dialogo) => void dialogo.accept());
  await page.getByRole("button", { name: "Pular este mês" }).click();
  await historico(page);
  await expect(previstos).toHaveCount(2);

  await abrirRecorrencia(page, previstos.nth(0), descricao);
  page.once("dialog", (dialogo) => {
    expect(dialogo.message()).toContain("o atrasado e o realizado ficam");
    void dialogo.accept();
  });
  await page.getByRole("button", { name: "Excluir a recorrência" }).click();
  await historico(page);
  await expect(previstos).toHaveCount(0);
  await expect.poll(async () => (await api.ler("/api/recorrencias")).some((r: { id: string }) => r.id === regra.id)).toBe(false);
});

test("sem internet, encerrar e mudar daqui para frente ficam na fila, um pedido cada, e sobem quando a rede volta", async ({ page, context }) => {
  const { descricao, regra, api } = await prepararRegra(page, 3);
  const previstos = linha(page, descricao);

  await context.setOffline(true);
  await abrirRecorrencia(page, previstos.nth(1), descricao);
  await page.getByRole("button", { name: "Encerrar depois desta vez" }).click();
  await historico(page);
  // O aparelho já esconde o previsto que o fim vai tirar; o servidor faz o resto ao receber.
  await expect(previstos).toHaveCount(2);
  const naoEnviadas = page.getByRole("region", { name: "Mudanças de recorrência não enviadas" });
  await expect(naoEnviadas).toContainText(`${descricao}: termina na 2ª vez, não enviado`);

  await abrirRecorrencia(page, previstos.nth(1), descricao);
  // A tela já mostra a regra com a mudança não enviada por cima.
  await expect(page.getByRole("listitem").filter({ hasText: "termina na 2ª vez, não enviado" })).toBeVisible();
  await mudarOValor(page, "210,00");
  await expect(naoEnviadas.getByRole("listitem")).toHaveCount(2);
  await expect(naoEnviadas).toContainText(`${descricao}: valor, não enviado`);
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("2 mudanças de recorrência não enviadas");

  await context.setOffline(false);
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  await aba(page, "Histórico");
  await expect(naoEnviadas).toHaveCount(0);
  await expect(previstos).toHaveCount(2);
  await expect(previstos.nth(0)).toContainText("− R$ 210,00");
  await expect(previstos.nth(1)).toContainText("− R$ 210,00");
  const [gravada] = (await api.ler("/api/recorrencias")).filter((r: { id: string }) => r.id === regra.id);
  expect(gravada).toMatchObject({ valor_centavos: 21000, vezes: 2, ate: null });
});

/** Muda a regra pela API, como a outra pessoa com internet, fora do contexto que está sem rede. */
async function mudarPelaApi(request: APIRequestContext, token: string, id: string, data: object) {
  const resposta = await request.patch(`/api/recorrencias/${id}`, { headers: { authorization: token }, data });
  expect(resposta.ok(), await resposta.text()).toBe(true);
}

test("a mudança sem internet sobre um campo que mudou depois é recusada, e a edição do mês vira conflito vindo da regra", async ({ page, context, request }) => {
  const { descricao, regra } = await prepararRegra(page, 2);
  const token = await tokenDaPagina(page);
  await aba(page, "Histórico");
  const previstos = linha(page, descricao);
  await expect(previstos).toHaveCount(2);

  await context.setOffline(true);
  await abrirRecorrencia(page, previstos.nth(1), descricao);
  await mudarOValor(page, "195,00");
  // Só este mês, na 2ª vez: R$ 189,90 + "7" no teclado.
  await previstos.nth(0).getByRole("link", { name: `Editar ${descricao}` }).click();
  await digitar(page, "7");
  await page.getByRole("button", { name: "Salvar" }).click();
  await historico(page);
  await mudarPelaApi(request, token, regra.id, { a_partir_da_ocorrencia: 1, valor_centavos: 21000 });

  await context.setOffline(false);
  const naoEnviadas = page.getByRole("region", { name: "Mudanças de recorrência não enviadas" });
  await expect(naoEnviadas).toContainText(`${descricao}: valor, não enviado: a regra mudou depois (valor): confira e mude de novo`);
  await expect(previstos.nth(0)).toContainText("⚠ conflito");
  await naoEnviadas.getByRole("button", { name: `Descartar a mudança de ${descricao}` }).click();
  await expect(naoEnviadas).toHaveCount(0);

  await previstos.nth(0).getByRole("link", { name: `Decidir ${descricao}` }).click();
  await expect(page.getByText(`O da regra a recorrência ${descricao}`).first()).toBeVisible();
});

/** Abre o novo lançamento, preenche e marca "Recorrente", todo mês por 2 vezes a partir de hoje. */
async function lancarRecorrente(page: Page, { conta, casa, descricao }: { conta: string; casa: string; descricao: string }) {
  await aba(page, "Hoje");
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, "1", "8", "9", "9", "0");
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: casa }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(descricao);
  await page.getByRole("group", { name: "Repete?" }).getByRole("button", { name: "Recorrente" }).click();
  await page.getByRole("group", { name: "Termina" }).getByRole("button", { name: "Depois de" }).click();
  await page.getByLabel("Vezes").fill("2");
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await historico(page);
}

async function prepararCasal(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, casa, descricao] = [`Corrente ${s}`, `Casa ${s}`, `Luz ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", casa, "despesa");
  return { conta, casa, descricao };
}

test("a recorrência criada que talvez já esteja no servidor se exclui em vez de se descartar", async ({ page, context }) => {
  const { conta, casa, descricao } = await prepararCasal(page);
  await context.setOffline(true);
  await lancarRecorrente(page, { conta, casa, descricao });

  // O servidor grava o lote, mas a resposta não chega ao aparelho.
  let perdidas = 0;
  await page.route("**/api/lancamentos/lote", async (rota) => {
    if (perdidas > 0) return rota.continue();
    perdidas++;
    await rota.fetch();
    await rota.abort("connectionreset");
  });
  await context.setOffline(false);
  await expect.poll(() => perdidas).toBe(1);

  const criadas = page.getByRole("region", { name: "Recorrências não enviadas" });
  await expect(criadas).toContainText("talvez já esteja no servidor");
  page.once("dialog", (dialogo) => void dialogo.accept());
  await criadas.getByRole("button", { name: `Excluir ${descricao}` }).click();
  await expect(criadas).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Mudanças de recorrência não enviadas" })).toContainText(`${descricao}: excluir`);

  // Com internet, a exclusão sobe na hora.
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  await aba(page, "Histórico");
  await expect(linha(page, descricao)).toHaveCount(0);
  const api = await apiDaPagina(page);
  expect((await api.ler("/api/recorrencias")).filter((r: { descricao: string }) => r.descricao === descricao)).toEqual([]);
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("a recorrência descartada no meio do envio chega ao servidor e sai de lá também", async ({ page, context }) => {
  const { conta, casa, descricao } = await prepararCasal(page);
  await context.setOffline(true);
  await lancarRecorrente(page, { conta, casa, descricao });

  // O envio sai e fica parado no caminho enquanto a pessoa descarta.
  let soltar = () => {};
  const solto = new Promise<void>((resolve) => (soltar = resolve));
  let parados = 0;
  await page.route("**/api/lancamentos/lote", async (rota) => {
    if (parados++ === 0) await solto;
    await rota.continue();
  });
  await context.setOffline(false);
  await expect.poll(() => parados).toBe(1);
  const criadas = page.getByRole("region", { name: "Recorrências não enviadas" });
  await criadas.getByRole("button", { name: `Descartar ${descricao}` }).click();
  await expect(criadas).toHaveCount(0);
  soltar();

  // O aparelho manda a exclusão logo depois: os previstos não ficam no servidor.
  await expect.poll(() => parados).toBe(2);
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  const api = await apiDaPagina(page);
  expect((await api.ler("/api/recorrencias")).filter((r: { descricao: string }) => r.descricao === descricao)).toEqual([]);
  await aba(page, "Histórico");
  await expect(linha(page, descricao)).toHaveCount(0);
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("quando quem envia é o service worker, ele lê de novo os previstos que a mudança da regra refez", async ({ page, context }) => {
  const { descricao } = await prepararRegra(page, 2);
  await page.evaluate(() => navigator.serviceWorker.ready);
  const previstos = linha(page, descricao);

  // A página não consegue enviar (só o pedido dela é barrado); o service worker não passa por esta rota.
  await page.route("**/api/lancamentos/lote", (rota) => rota.abort("connectionreset"));
  await abrirRecorrencia(page, previstos.nth(1), descricao);
  await mudarOValor(page, "210,00");
  const naoEnviadas = page.getByRole("region", { name: "Mudanças de recorrência não enviadas" });
  await expect(naoEnviadas).toContainText(`${descricao}: valor, não enviado`);

  // O `sync` que a página pediu, como o Android o dispara quando a rede volta.
  const cdp = await context.newCDPSession(page);
  const registro = new Promise<string>((resolve) =>
    cdp.on("ServiceWorker.workerRegistrationUpdated", ({ registrations }) => registrations[0] && resolve(registrations[0].registrationId)),
  );
  await cdp.send("ServiceWorker.enable");
  await cdp.send("ServiceWorker.dispatchSyncEvent", { origin: "http://127.0.0.1:4173", registrationId: await registro, tag: "enviar-fila", lastChance: false });

  // A página não leu nada de novo: a lista guardada mudou pelo service worker.
  await expect(naoEnviadas).toHaveCount(0);
  await expect(previstos.nth(0)).toContainText("− R$ 210,00");
  await expect(previstos.nth(1)).toContainText("− R$ 210,00");
  await page.unrouteAll({ behavior: "ignoreErrors" });
});
