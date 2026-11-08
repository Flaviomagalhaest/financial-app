// A aba aberta numa versão anterior do app (ticket 168): ela recarrega sozinha quando o service
// worker novo assume e quando o banco do aparelho já está numa versão mais nova que o código dela.
import { expect, test, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { entrar } from "./entrar";
import { esperarFilaVazia } from "./fila";
import { cadastrar, lancar } from "./lancar";

/** Marca a página carregada; a marca some quando a aba recarrega. */
const marcar = (page: Page) => page.evaluate(() => void ((window as unknown as { __semRecarga: boolean }).__semRecarga = true));
const semRecarga = (page: Page) => page.evaluate(() => (window as unknown as { __semRecarga?: boolean }).__semRecarga === true);

/**
 * Publica uma versão nova do app enquanto `passo` roda: o service worker servido muda um caractere
 * da versão, sem mudar de tamanho (o `vite preview` guarda o tamanho dos arquivos ao subir). Mexe no
 * `dist/` que todos os testes servem: só vale com um teste por vez (`workers: 1`).
 */
async function comVersaoNova(passo: () => Promise<void>) {
  const arquivo = new URL("../dist/service-worker.js", import.meta.url);
  const original = readFileSync(arquivo, "utf8");
  writeFileSync(arquivo, original.replace(/const VERSAO = "(.)/, (_, letra) => `const VERSAO = "${letra === "x" ? "y" : "x"}`));
  try {
    await passo();
  } finally {
    writeFileSync(arquivo, original);
  }
}

/** O service worker no controle da página. */
async function instalarCasca(page: Page) {
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
}

test("a aba aberta recarrega quando o service worker de uma versão nova assume", async ({ page }) => {
  await page.goto("/");
  await entrar(page);
  await instalarCasca(page);

  // Com um lançamento sendo digitado: ele se perde (decisão do dono).
  await page.getByRole("link", { name: "Novo lançamento" }).click();
  await page.getByRole("button", { name: "7", exact: true }).click();
  await marcar(page);
  await comVersaoNova(async () => {
    const recarga = page.waitForEvent("load");
    await page.evaluate(() => navigator.serviceWorker.getRegistration().then((registro) => registro!.update()));
    await recarga;
  });

  expect(await semRecarga(page)).toBe(false);
  await expect(page.getByLabel("Conta de flavio@teste.com")).toBeVisible();
});

test("a primeira instalação do service worker não recarrega a aba", async ({ page }) => {
  let cargas = 0;
  page.on("load", () => cargas++);
  await page.goto("/");
  await entrar(page);
  // Sem o reload de `instalarCasca`: o `clients.claim` põe a página sob o service worker.
  await page.evaluate(() => navigator.serviceWorker.ready);
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);

  expect(cargas).toBe(1);
});

const BANCO = "financial-app-dados";

/**
 * O código da versão nova do banco: depois de `publicarBancoNovo`, a página que carrega pede o
 * banco na versão 3 em vez da 2 (a 3 não muda as lojas). A página já aberta segue com o código
 * anterior, que pede a 2, até recarregar.
 */
function codigoDoBancoNovo(banco: string) {
  if (localStorage.getItem("__banco-novo") !== "1") return;
  const abrir = indexedDB.open.bind(indexedDB);
  indexedDB.open = (nome: string, versao?: number) => abrir(nome, nome === banco && versao === 2 ? 3 : versao);
}

/** Abre o banco na versão 3, como faria a primeira aba com o código novo. */
const abrirNaVersao3 = (page: Page) =>
  page.evaluate(
    (banco) =>
      new Promise<void>((resolve, reject) => {
        const abertura = indexedDB.open(banco, 3);
        abertura.onsuccess = () => {
          abertura.result.close();
          resolve();
        };
        abertura.onerror = () => reject(abertura.error);
      }),
    BANCO,
  );

const aba = (page: Page, nome: string) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome }).click();

async function prepararCasal(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, mercado] = [`Corrente ${s}`, `Mercado ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  return { s, conta, mercado };
}

test("a aba anterior recarrega quando outra aba sobe o banco do aparelho e volta a ler e lançar", async ({ page, context }) => {
  await context.addInitScript(codigoDoBancoNovo, BANCO);
  const { s, conta, mercado } = await prepararCasal(page);
  await lancar(page, { teclas: ["1", "2", "00"], conta, categoria: mercado, descricao: `Feira ${s}` });
  await esperarFilaVazia(page);
  await marcar(page);

  // A versão nova abre noutra aba e sobe o banco. A aba anterior lê o banco (no aviso da outra aba
  // ou na próxima tela), recebe `VersionError` e recarrega com o código novo.
  const recarga = page.waitForEvent("load");
  await page.evaluate(() => localStorage.setItem("__banco-novo", "1"));
  const nova = await context.newPage();
  await nova.goto("/");
  await abrirNaVersao3(nova);
  await nova.close();
  await aba(page, "Hoje");
  await recarga;
  expect(await semRecarga(page)).toBe(false);

  await aba(page, "Histórico");
  await expect(page.getByRole("listitem").filter({ hasText: `Feira ${s}` })).toContainText("− R$ 12,00");
  await lancar(page, { teclas: ["3", "4", "00"], conta, categoria: mercado, descricao: `Padaria ${s}` });
  await esperarFilaVazia(page);
  await expect(page.getByRole("listitem").filter({ hasText: `Padaria ${s}` })).toContainText("− R$ 34,00");
});

test("com o banco mais novo que o código, a aba recarrega uma vez só", async ({ page, context }) => {
  await prepararCasal(page);
  let cargas = 0;
  page.on("load", () => cargas++);

  const nova = await context.newPage();
  await nova.goto("/");
  await abrirNaVersao3(nova);
  await nova.close();

  // O código da aba pede a versão 2: recarregar não resolve, e a segunda leitura não recarrega.
  await aba(page, "Hoje");
  await expect.poll(() => cargas).toBe(1);
  await expect(page.getByRole("navigation", { name: "Telas" })).toBeVisible();
  await aba(page, "Histórico");
  await aba(page, "Hoje");
  await page.waitForTimeout(2_000);
  expect(cargas).toBe(1);
});
