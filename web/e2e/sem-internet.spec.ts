import { expect, test, type Page } from "@playwright/test";
import { renovacoes } from "./cognito-falso";
import { entrar } from "./entrar";
import { cadastrar, lancar } from "./lancar";

/** Entra, cadastra uma conta e uma categoria de despesa e deixa as duas guardadas no aparelho. */
async function prepararCasal(page: Page, email?: string) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, mercado] = [`Corrente ${s}`, `Mercado ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page, email);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  return { s, conta, mercado };
}

const aba = (page: Page, nome: string) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome }).click();

test("lança sem internet, mostra ⏳ e a contagem na Hoje e envia uma vez só quando a rede volta", async ({ page, context }) => {
  const { s, conta, mercado } = await prepararCasal(page);

  await context.setOffline(true);
  await lancar(page, { teclas: ["4", "5", "00"], conta, categoria: mercado, descricao: `Padaria ${s}` });

  const linha = page.getByRole("listitem").filter({ hasText: `Padaria ${s}` });
  await expect(linha).toContainText("− R$ 45,00");
  await expect(linha).toContainText("⏳ não enviado");
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("1 lançamento não enviado");

  await context.setOffline(false);
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  await aba(page, "Histórico");
  await expect(linha).not.toContainText("não enviado");
  await page.reload();
  await expect(linha).toHaveCount(1);
  await expect(linha).toContainText("− R$ 45,00");
});

test("edita e exclui sem internet e, se a resposta do envio se perde, reenviar não duplica", async ({ page, context }) => {
  const { s, conta, mercado } = await prepararCasal(page);
  await lancar(page, { teclas: ["1", "00"], conta, categoria: mercado, descricao: `Feira ${s}` });
  await lancar(page, { teclas: ["2", "00"], conta, categoria: mercado, descricao: `Farmácia ${s}` });
  const feira = page.getByRole("listitem").filter({ hasText: `Feira ${s}` });
  const farmacia = page.getByRole("listitem").filter({ hasText: `Farmácia ${s}` });
  await expect(feira).not.toContainText("não enviado");
  await expect(farmacia).not.toContainText("não enviado");

  await context.setOffline(true);
  await feira.getByRole("link", { name: `Editar Feira ${s}` }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 1,00");
  await page.getByRole("button", { name: "7", exact: true }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(feira).toContainText("− R$ 10,07");
  await expect(feira).toContainText("⏳ não enviado");
  page.once("dialog", (dialogo) => void dialogo.accept());
  await farmacia.getByRole("button", { name: `Excluir Farmácia ${s}` }).click();
  await expect(farmacia).toHaveCount(0);
  await lancar(page, { teclas: ["3", "00"], conta, categoria: mercado, descricao: `Açougue ${s}` });
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("3 lançamentos não enviados");

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
  await expect(page.getByTestId("nao-enviados")).toContainText("3 lançamentos não enviados");

  await page.getByRole("button", { name: "Enviar agora" }).click();
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  await page.reload();
  await aba(page, "Histórico");
  await expect(feira).toHaveCount(1);
  await expect(feira).toContainText("− R$ 10,07");
  await expect(farmacia).toHaveCount(0);
  await expect(page.getByRole("listitem").filter({ hasText: `Açougue ${s}` })).toHaveCount(1);
});

test("recusado pelo servidor fica 'não enviado: <motivo>' para corrigir ou descartar, e o resto da fila sobe", async ({ page, context }) => {
  // O aparelho guardou uma conta que o servidor não tem mais (como um cartão arquivado depois).
  const sumida = `Conta sumida ${Date.now()}`;
  await page.route("**/api/contas", async (rota) => {
    if (rota.request().method() !== "GET") return rota.continue();
    const resposta = await rota.fetch();
    const contas = await resposta.json();
    await rota.fulfill({ response: resposta, json: [...contas, { id: crypto.randomUUID(), nome: sumida, tipo: "corrente" }] });
  });
  const { s, conta, mercado } = await prepararCasal(page);

  await context.setOffline(true);
  await lancar(page, { teclas: ["1", "1"], conta: sumida, categoria: mercado, descricao: `Corrigir ${s}` });
  await lancar(page, { teclas: ["2", "2"], conta, categoria: mercado, descricao: `Bom ${s}` });
  await lancar(page, { teclas: ["3", "3"], conta: sumida, categoria: mercado, descricao: `Descartar ${s}` });
  await context.setOffline(false);

  const corrigir = page.getByRole("listitem").filter({ hasText: `Corrigir ${s}` });
  const bom = page.getByRole("listitem").filter({ hasText: `Bom ${s}` });
  const descartar = page.getByRole("listitem").filter({ hasText: `Descartar ${s}` });
  await expect(corrigir).toContainText("não enviado: conta não encontrada");
  await expect(descartar).toContainText("não enviado: conta não encontrada");
  await expect(bom).not.toContainText("não enviado");
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("2 lançamentos não enviados (2 recusados");

  await aba(page, "Histórico");
  await descartar.getByRole("button", { name: `Descartar Descartar ${s}` }).click();
  await expect(descartar).toHaveCount(0);
  await corrigir.getByRole("link", { name: `Corrigir Corrigir ${s}` }).click();
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(corrigir).toContainText(conta);
  await expect(corrigir).not.toContainText("não enviado");

  await page.reload();
  await expect(corrigir).toHaveCount(1);
  await expect(bom).toHaveCount(1);
  await expect(descartar).toHaveCount(0);
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  // Uma leitura das contas ainda em andamento não pode estourar no teste seguinte.
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

/** O service worker só controla a página depois de uma recarga; aí ela abre sem internet. */
async function instalarCasca(page: Page) {
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
}

test("sem internet, as telas abertas mostram a última resposta com 'atualizado às' e contas e categorias precisam de internet", async ({ page, context }) => {
  const { s, conta, mercado } = await prepararCasal(page);
  await lancar(page, { teclas: ["9", "00"], conta, categoria: mercado, descricao: `Guardado ${s}` });
  const linha = page.getByRole("listitem").filter({ hasText: `Guardado ${s}` });
  await expect(linha).not.toContainText("não enviado");
  await instalarCasca(page);

  await context.setOffline(true);
  await page.reload();
  await expect(linha).toContainText("− R$ 9,00");
  await expect(page.getByText(/Sem internet: atualizado às \d\d:\d\d/)).toBeVisible();

  await page.goto("/#/contas-e-categorias");
  await expect(page.getByRole("listitem").filter({ hasText: conta })).toBeVisible();
  const novaConta = page.getByRole("form", { name: "Nova conta" });
  await expect(novaConta.getByRole("button", { name: "Cadastrar" })).toBeDisabled();
  await expect(page.getByRole("button", { name: `Arquivar conta ${conta}` })).toBeDisabled();
  await expect(page.getByText("Mudar contas e categorias precisa de internet.")).toBeVisible();

  await context.setOffline(false);
  await expect(novaConta.getByRole("button", { name: "Cadastrar" })).toBeEnabled();
  await expect(page.getByText(/atualizado às/)).toHaveCount(0);
});

test("rede que não responde: a tela mostra a resposta guardada, o lançamento fica não enviado e sobe quando a rede responde", async ({ page }) => {
  const { s, conta, mercado } = await prepararCasal(page);
  await lancar(page, { teclas: ["9", "00"], conta, categoria: mercado, descricao: `Guardado ${s}` });
  const guardado = page.getByRole("listitem").filter({ hasText: `Guardado ${s}` });
  await expect(guardado).not.toContainText("não enviado");

  // O Wi-Fi diz que há rede (navigator.onLine), mas nenhuma chamada da API recebe resposta.
  let respondendo = false;
  await page.route("**/api/**", (rota) => (respondendo ? rota.continue() : undefined));
  await page.reload();
  await expect(guardado).toContainText("− R$ 9,00");
  await expect(page.getByText(/Sem internet: atualizado às \d\d:\d\d/)).toBeVisible({ timeout: 20_000 });

  await lancar(page, { teclas: ["4", "00"], conta, categoria: mercado, descricao: `Mudo ${s}` });
  const mudo = page.getByRole("listitem").filter({ hasText: `Mudo ${s}` });
  await expect(mudo).toContainText("⏳ não enviado");
  await page.goto("/#/contas-e-categorias");
  await expect(page.getByRole("form", { name: "Nova conta" }).getByRole("button", { name: "Cadastrar" })).toBeDisabled();

  respondendo = true;
  await aba(page, "Hoje");
  await page.getByRole("button", { name: "Enviar agora" }).click();
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0, { timeout: 20_000 });
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("sair com lançamentos não enviados pede confirmação e, confirmado, apaga a fila do aparelho", async ({ page, context }) => {
  const { s, conta, mercado } = await prepararCasal(page, "esposa@teste.com");
  await context.setOffline(true);
  await lancar(page, { teclas: ["5"], conta, categoria: mercado, descricao: `Antes de sair ${s}` });

  let mensagem = "";
  page.once("dialog", (dialogo) => {
    mensagem = dialogo.message();
    void dialogo.dismiss();
  });
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect.poll(() => mensagem).toContain("1 lançamento ainda não foi enviado");
  await expect(page.getByText("Entrou como esposa@teste.com")).toBeVisible();

  page.once("dialog", (dialogo) => void dialogo.accept());
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page.getByLabel("Senha")).toBeVisible();

  await context.setOffline(false);
  await entrar(page, "esposa@teste.com");
  await expect(page.getByText("Entrou como esposa@teste.com")).toBeVisible();
  await aba(page, "Hoje");
  await expect(page.getByTestId("estado-da-api")).toHaveText("API no ar");
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  await aba(page, "Histórico");
  await expect(page.getByRole("listitem").filter({ hasText: `Antes de sair ${s}` })).toHaveCount(0);
});

test("o aviso de não enviado fica em destaque depois de 24 h", async ({ page, context }) => {
  await page.clock.install();
  const { s, conta, mercado } = await prepararCasal(page);
  await context.setOffline(true);
  await lancar(page, { teclas: ["8"], conta, categoria: mercado, descricao: `Esquecido ${s}` });
  await aba(page, "Hoje");
  const aviso = page.getByTestId("nao-enviados");
  await expect(aviso).toContainText("1 lançamento não enviado");
  await expect(aviso).not.toContainText("abra com internet para enviar");

  await page.clock.fastForward("23:00:00");
  await expect(aviso).not.toContainText("abra com internet para enviar");
  await page.clock.fastForward("01:01:00");
  await expect(aviso).toContainText("Há mais de 24 h sem enviar: abra com internet para enviar.");
  await expect(aviso).toHaveClass("aviso");
});

test("no Android, o service worker sobe a fila em segundo plano, sem o app aberto", async ({ page, context, browser }) => {
  const { s, conta, mercado } = await prepararCasal(page);
  await instalarCasca(page);
  await context.setOffline(true);
  await lancar(page, { teclas: ["6", "00"], conta, categoria: mercado, descricao: `Segundo plano ${s}` });

  // Fecha o app (a aba sai dele) e a rede volta: quem envia é o `sync` do service worker.
  const cdp = await context.newCDPSession(page);
  const registro = new Promise<string>((resolve) =>
    cdp.on("ServiceWorker.workerRegistrationUpdated", ({ registrations }) => {
      const nosso = registrations.find((r) => r.scopeURL.startsWith("http://127.0.0.1:4173") && !r.isDeleted);
      if (nosso) resolve(nosso.registrationId);
    }),
  );
  await cdp.send("ServiceWorker.enable");
  const registrationId = await registro;
  // Com o app fechado há tempo, o token de acesso guardado já venceu: o service worker renova.
  await page.evaluate(
    () =>
      new Promise((resolve, reject) => {
        const abrir = indexedDB.open("financial-app-login");
        abrir.onsuccess = () => {
          const loja = abrir.result.transaction("sessao", "readwrite").objectStore("sessao");
          const ler = loja.get("atual");
          ler.onsuccess = () => (loja.put({ ...ler.result, acessoVenceEm: 0 }, "atual").onsuccess = resolve);
        };
        abrir.onerror = reject;
      }),
  );
  const renovadasAntes = await renovacoes();
  await page.goto("about:blank");
  await context.setOffline(false);
  await cdp.send("ServiceWorker.dispatchSyncEvent", { origin: "http://127.0.0.1:4173", registrationId, tag: "enviar-fila", lastChance: false });

  // A outra pessoa, noutro aparelho, já vê o lançamento.
  const outro = await browser.newContext({ baseURL: "http://127.0.0.1:4173" });
  const esposa = await outro.newPage();
  await esposa.goto("/#/historico");
  await entrar(esposa, "esposa@teste.com");
  await expect(esposa.getByText("Entrou como esposa@teste.com")).toBeVisible();
  const linha = esposa.getByRole("listitem").filter({ hasText: `Segundo plano ${s}` });
  await expect(async () => {
    await esposa.reload();
    await expect(linha).toContainText("− R$ 6,00", { timeout: 1000 });
  }).toPass();
  await outro.close();
  expect(await renovacoes()).toBe(renovadasAntes + 1);

  await page.goto("/#/hoje");
  await expect(page.getByTestId("estado-da-api")).toHaveText("API no ar");
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
});

test("criado com a resposta perdida e depois editado ou excluído sem internet: a mudança não se perde", async ({ page, context }) => {
  const { s, conta, mercado } = await prepararCasal(page);
  // O servidor grava os dois lançamentos, mas a resposta não chega ao aparelho.
  let perdidas = 0;
  await page.route("**/api/lancamentos/lote", async (rota) => {
    if (perdidas > 0) return rota.continue();
    perdidas++;
    await rota.fetch();
    await rota.abort("connectionreset");
  });
  await context.setOffline(true);
  await lancar(page, { teclas: ["1"], conta, categoria: mercado, descricao: `Editado ${s}` });
  await lancar(page, { teclas: ["2"], conta, categoria: mercado, descricao: `Excluído ${s}` });
  await context.setOffline(false);
  await expect.poll(() => perdidas).toBe(1);

  await context.setOffline(true);
  const editado = page.getByRole("listitem").filter({ hasText: `Editado ${s}` });
  const excluido = page.getByRole("listitem").filter({ hasText: `Excluído ${s}` });
  await editado.getByRole("link", { name: `Editar Editado ${s}` }).click();
  await page.getByRole("button", { name: "9", exact: true }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(editado).toContainText("− R$ 0,19");
  page.once("dialog", (dialogo) => void dialogo.accept());
  await excluido.getByRole("button", { name: `Excluir Excluído ${s}` }).click();
  await expect(excluido).toHaveCount(0);

  await context.setOffline(false);
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toHaveCount(0);
  await page.reload();
  await aba(page, "Histórico");
  await expect(editado).toContainText("− R$ 0,19");
  await expect(excluido).toHaveCount(0);
});
