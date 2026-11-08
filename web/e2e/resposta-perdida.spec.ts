import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { cadastrar, digitar, lancar } from "./lancar";

// A edição chega ao servidor, mas a resposta não volta ao aparelho, e a pessoa reabre o app (ticket 169).

const linhaDe = (page: Page, texto: string) => page.getByRole("listitem").filter({ hasText: texto });

/** Outra aba segura a trava da fila: ao abrir, o envio espera até a função devolvida ser chamada. */
async function segurarAFila(page: Page): Promise<() => Promise<void>> {
  const outra = page;
  await outra.goto("/service-worker.js");
  await outra.evaluate(
    () =>
      new Promise<void>((segurou) => {
        void navigator.locks.request("financial-app-fila", { mode: "exclusive" }, () => {
          segurou();
          return new Promise<void>((soltar) => ((window as unknown as { soltarFila: () => void }).soltarFila = soltar));
        });
      }),
  );
  return () => outra.evaluate(() => (window as unknown as { soltarFila: () => void }).soltarFila());
}

/**
 * Lança "Jantar <s>" de R$ 1,00 e o edita para R$ 10,07: o servidor grava a edição, mas a resposta
 * cai (`"resposta"`) ou a pessoa recarrega antes de ela voltar (`"recarga"`). Depois recarrega, com
 * o envio da fila parado até `soltar()`: a próxima mudança entra no lugar da edição, como quando
 * a pessoa mexe antes de a fila subir.
 */
async function editarSemResposta(page: Page, perder: "resposta" | "recarga") {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, mercado, descricao] = [`Corrente ${s}`, `Mercado ${s}`, `Jantar ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  await lancar(page, { teclas: ["1", "00"], conta, categoria: mercado, descricao });
  const linha = linhaDe(page, descricao);
  await expect(linha).not.toContainText("não enviado");

  let gravadas = 0;
  await page.route("**/api/lancamentos/lote", async (rota) => {
    if (gravadas > 0) return rota.continue();
    await rota.fetch();
    gravadas++;
    if (perder === "resposta") await rota.abort("connectionreset");
    // Na recarga, o pedido fica sem resposta até a página sair.
  });
  await linha.getByRole("link", { name: `Editar ${descricao}` }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 1,00");
  await digitar(page, "7");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(linha).toContainText("− R$ 10,07");
  await expect.poll(() => gravadas).toBe(1);
  await expect(linha).toContainText("não enviado");

  const soltar = await segurarAFila(await page.context().newPage());
  await page.reload();
  await expect(linha).toContainText("− R$ 10,07");
  await expect(linha).toContainText("não enviado");
  return { linha, descricao, soltar, api: await apiDaPagina(page) };
}

for (const perder of ["resposta", "recarga"] as const) {
  test(`excluir ao reabrir, sobre a edição sem ${perder}, não vira conflito`, async ({ page }) => {
    const { linha, descricao, soltar, api } = await editarSemResposta(page, perder);
    page.once("dialog", (dialogo) => void dialogo.accept());
    await linha.getByLabel(`Mais ações ${descricao}`).click();
    await linha.getByRole("button", { name: `Excluir ${descricao}` }).click();
    await expect(linha).toHaveCount(0);
    await soltar();

    await expect.poll(async () => (await api.ler("/api/lancamentos")).some((l: { descricao: string }) => l.descricao === descricao)).toBe(false);
    await page.reload();
    await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
    await expect(linha).toHaveCount(0);
    await expect(page.getByText("conflito")).toHaveCount(0);
  });
}

test("editar de novo ao reabrir, sobre a edição sem resposta, não vira conflito", async ({ page }) => {
  const { linha, descricao, soltar, api } = await editarSemResposta(page, "resposta");
  await linha.getByRole("link", { name: `Editar ${descricao}` }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 10,07");
  await digitar(page, "Apagar", "8");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(linha).toContainText("− R$ 10,08");
  await soltar();

  await expect(linha).not.toContainText("não enviado");
  await expect(linha).not.toContainText("conflito");
  await expect
    .poll(async () => (await api.ler("/api/lancamentos")).find((l: { descricao: string }) => l.descricao === descricao)?.valor_centavos)
    .toBe(1008);
});

test("a edição sem resposta sobe sozinha ao reabrir o app", async ({ page }) => {
  const { linha, soltar } = await editarSemResposta(page, "resposta");
  await soltar();
  // Sem a pessoa mexer de novo: a fila sobe ao abrir.
  await expect(linha).not.toContainText("não enviado");
  await expect(linha).not.toContainText("conflito");
});

// O criar chega ao servidor, mas a página sai antes de a resposta voltar, e a pessoa exclui ao
// reabrir (ticket 173). Na recarga, o navegador derruba o pedido e a página ainda vê a falha; com a
// aba fechada (ou o app morto pelo sistema), ela não vê nada.
for (const sair of ["recarga", "aba fechada"] as const) {
  test(`excluir ao reabrir, sobre o criar sem resposta (${sair}), tira o lançamento do servidor`, async ({ page }) => {
    const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
    const [conta, mercado, descricao] = [`Corrente ${s}`, `Mercado ${s}`, `Jantar ${s}`];
    await page.goto("/#/contas-e-categorias");
    await entrar(page);
    await cadastrar(page, "Nova conta", conta, "corrente");
    await cadastrar(page, "Nova categoria", mercado, "despesa");

    let gravadas = 0;
    await page.route("**/api/lancamentos/lote", async (rota) => {
      if (gravadas > 0) return rota.continue();
      await rota.fetch();
      gravadas++;
      // O pedido fica sem resposta até a página sair.
    });
    await lancar(page, { teclas: ["1", "00"], conta, categoria: mercado, descricao });
    await expect.poll(() => gravadas).toBe(1);
    await expect(linhaDe(page, descricao)).toContainText("não enviado");

    const contexto = page.context();
    if (sair === "aba fechada") await page.close();
    const soltar = await segurarAFila(await contexto.newPage());
    if (sair === "aba fechada") {
      page = await contexto.newPage();
      await page.goto("/#/historico");
    } else await page.reload();
    const linha = linhaDe(page, descricao);
    await expect(linha).toContainText("não enviado");
    const api = await apiDaPagina(page);
    const noServidor = async () => (await api.ler("/api/lancamentos")).some((l: { descricao: string }) => l.descricao === descricao);
    expect(await noServidor()).toBe(true);

    page.once("dialog", (dialogo) => void dialogo.accept());
    await linha.getByLabel(`Mais ações ${descricao}`).click();
    await linha.getByRole("button", { name: `Excluir ${descricao}` }).click();
    await expect(linha).toHaveCount(0);
    await soltar();

    await expect.poll(noServidor).toBe(false);
    await page.reload();
    await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
    await expect(linha).toHaveCount(0);
    await expect(page.getByText("conflito")).toHaveCount(0);
  });
}

// O mesmo com a regra (ticket 181): a recorrência sai, chega ao servidor e a aba fecha antes da
// resposta. Ao reabrir, descartá-la deixaria os previstos no servidor. Sem rede, o pedido nem sai,
// e ela segue descartável.
for (const rede of ["com rede", "sem rede"] as const) {
  test(`a recorrência criada com a aba fechada no meio do envio (${rede}), ao reabrir`, async ({ page }) => {
    const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
    const [conta, casa, descricao] = [`Corrente ${s}`, `Casa ${s}`, `Luz ${s}`];
    await page.goto("/#/contas-e-categorias");
    await entrar(page);
    await cadastrar(page, "Nova conta", conta, "corrente");
    await cadastrar(page, "Nova categoria", casa, "despesa");

    let gravadas = 0;
    await page.route("**/api/lancamentos/lote", async (rota) => {
      if (gravadas > 0) return rota.continue();
      await rota.fetch();
      gravadas++;
      // O pedido fica sem resposta até a página sair.
    });
    const contexto = page.context();
    if (rede === "sem rede") await contexto.setOffline(true);
    await lancar(page, { teclas: ["1", "8", "9", "9", "0"], conta, categoria: casa, descricao, vezes: 2 });
    const naoEnviadas = (p: Page) => p.getByRole("region", { name: "Recorrências não enviadas" });
    await expect(naoEnviadas(page)).toContainText(`${descricao}, `);
    if (rede === "com rede") await expect.poll(() => gravadas).toBe(1);

    await page.close();
    if (rede === "sem rede") await contexto.setOffline(false);
    const soltar = await segurarAFila(await contexto.newPage());
    page = await contexto.newPage();
    await page.goto("/#/historico");
    await expect(naoEnviadas(page)).toContainText(`${descricao}, `);
    const descartar = naoEnviadas(page).getByRole("button", { name: `Descartar ${descricao}` });
    if (rede === "sem rede") {
      await expect(descartar).toBeVisible();
      await soltar();
      return;
    }
    const api = await apiDaPagina(page);
    const noServidor = async () => (await api.ler("/api/recorrencias")).some((r: { descricao: string }) => r.descricao === descricao);
    expect(await noServidor()).toBe(true);
    // Talvez gravada: não se descarta, e a exclusão a tira do servidor.
    await expect(naoEnviadas(page)).toContainText("talvez já esteja no servidor");
    await expect(descartar).toHaveCount(0);
    page.once("dialog", (dialogo) => void dialogo.accept());
    await naoEnviadas(page).getByRole("button", { name: `Excluir ${descricao}` }).click();
    await expect(naoEnviadas(page)).toHaveCount(0);
    await soltar();
    await expect.poll(noServidor).toBe(false);
  });
}
