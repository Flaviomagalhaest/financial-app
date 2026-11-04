// O que o aparelho guarda (ticket 164): a lista lançamento por lançamento, o envio da fila gravando
// só os enviados, o aviso só para quem lê a resposta que mudou e um GET da lista por tela.
import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";
import { cadastrar, lancar } from "./lancar";
import { esperarFilaVazia } from "./fila";

const LISTA = "/api/lancamentos";
const daLista = (url: string) => new URL(url).pathname === LISTA;

async function prepararCasal(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, mercado] = [`Corrente ${s}`, `Mercado ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  return { s, conta, mercado };
}

/** O service worker no controle, para a tela abrir sem internet. */
async function instalarCasca(page: Page) {
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
}

const aba = (page: Page, nome: string) => page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome }).click();

/**
 * Roda antes do app: conta as leituras da lista guardada (as transações só de leitura que a leem) e
 * quantos lançamentos cada envio da fila grava (na transação que também mexe na fila). Vale para a
 * lista num bloco só, como era, e lançamento por lançamento.
 */
function contarNoArmazem(lista: string) {
  const contagem = { leiturasDaLista: 0, gravadosNoEnvio: 0 };
  (window as unknown as { __armazem: typeof contagem }).__armazem = contagem;
  const lidas = new WeakSet<IDBTransaction>();
  const escritas = new WeakMap<IDBTransaction, { gravados: number; naFila: boolean }>();
  const leu = (loja: IDBObjectStore) => {
    if (loja.transaction.mode !== "readonly" || lidas.has(loja.transaction)) return;
    lidas.add(loja.transaction);
    contagem.leiturasDaLista++;
  };
  const escrita = (loja: IDBObjectStore) => {
    let anotada = escritas.get(loja.transaction);
    if (!anotada) {
      const nova = { gravados: 0, naFila: false };
      escritas.set(loja.transaction, (anotada = nova));
      loja.transaction.addEventListener("complete", () => void (nova.naFila && (contagem.gravadosNoEnvio += nova.gravados)));
    }
    return anotada;
  };
  const { get, getAll, put, delete: apagar } = IDBObjectStore.prototype;
  IDBObjectStore.prototype.get = function (this: IDBObjectStore, chave: IDBValidKey | IDBKeyRange) {
    if (chave === lista && this.name === "respostas") leu(this);
    return get.call(this, chave);
  };
  IDBObjectStore.prototype.getAll = function (this: IDBObjectStore, ...args: unknown[]) {
    if (this.name === "lancamentos") leu(this);
    return (getAll as (...a: unknown[]) => IDBRequest).apply(this, args);
  };
  IDBObjectStore.prototype.put = function (this: IDBObjectStore, valor: unknown, chave?: IDBValidKey) {
    if (this.name === "fila") escrita(this).naFila = true;
    if (this.name === "respostas" && chave === lista) escrita(this).gravados += ((valor as { dados?: unknown[] }).dados ?? []).length;
    if (this.name === "lancamentos") escrita(this).gravados++;
    return put.call(this, valor, chave);
  };
  IDBObjectStore.prototype.delete = function (this: IDBObjectStore, chave: IDBValidKey | IDBKeyRange) {
    if (this.name === "fila") escrita(this).naFila = true;
    return apagar.call(this, chave);
  };
}

const contagem = (page: Page) => page.evaluate(() => ({ ...(window as unknown as { __armazem: { leiturasDaLista: number; gravadosNoEnvio: number } }).__armazem }));

test("abrir a tela de lançamento faz um GET da lista só", async ({ page }) => {
  await prepararCasal(page);
  // Troca o endereço sem `hashchange`: com `goto("/#/novo")` a tela abria já ali e pedia a lista, e
  // o reload logo abaixo cortava esse GET depois de o contador o ver (ticket 15 de processo-do-repositorio).
  await page.evaluate(() => history.replaceState(null, "", "/#/novo"));
  const lidas: string[] = [];
  page.on("request", (pedido) => void (daLista(pedido.url()) && pedido.method() === "GET" && lidas.push(pedido.url())));
  const primeira = page.waitForResponse((r) => daLista(r.url()) && r.request().method() === "GET");
  await page.reload();
  await expect(page.getByRole("heading", { name: "Novo lançamento" })).toBeVisible();
  await primeira;
  // As leituras que os hooks da tela pedem saem juntas, ao montar: depois da primeira resposta, não sai outra.
  await page.waitForTimeout(1500);
  expect(lidas).toHaveLength(1);
});

test("a resposta das categorias chega e a lista guardada não é relida", async ({ page }) => {
  await page.addInitScript(contarNoArmazem, LISTA);
  const { s, conta, mercado } = await prepararCasal(page);
  await lancar(page, { teclas: ["1", "00"], conta, categoria: mercado, descricao: `Feira ${s}` });
  await expect(page.getByRole("listitem").filter({ hasText: `Feira ${s}` })).not.toContainText("não enviado");

  let soltar = () => {};
  const solta = new Promise<void>((resolve) => (soltar = resolve));
  await page.route("**/api/categorias", async (rota) => {
    const resposta = await rota.fetch();
    await solta;
    await rota.fulfill({ response: resposta }).catch(() => undefined);
  });
  await page.reload();
  await expect(page.getByRole("listitem").filter({ hasText: `Feira ${s}` })).toContainText("− R$ 1,00");
  await page.waitForTimeout(1500);
  const antes = (await contagem(page)).leiturasDaLista;

  const chegou = page.waitForResponse((r) => new URL(r.url()).pathname === "/api/categorias");
  soltar();
  await chegou;
  await page.waitForTimeout(1500);
  expect((await contagem(page)).leiturasDaLista).toBe(antes);
});

test("o envio da fila grava no aparelho só o lançamento enviado, não a lista inteira", async ({ page, context }) => {
  await page.addInitScript(contarNoArmazem, LISTA);
  const { s, conta, mercado } = await prepararCasal(page);
  await lancar(page, { teclas: ["1", "00"], conta, categoria: mercado, descricao: `Feira ${s}` });
  await lancar(page, { teclas: ["2", "00"], conta, categoria: mercado, descricao: `Farmácia ${s}` });
  await expect(page.getByRole("listitem").filter({ hasText: `Farmácia ${s}` })).not.toContainText("não enviado");

  await context.setOffline(true);
  await lancar(page, { teclas: ["3", "00"], conta, categoria: mercado, descricao: `Açougue ${s}` });
  await aba(page, "Hoje");
  await expect(page.getByTestId("nao-enviados")).toContainText("1 lançamento não enviado");
  const antes = (await contagem(page)).gravadosNoEnvio;
  await context.setOffline(false);
  await esperarFilaVazia(page);
  expect((await contagem(page)).gravadosNoEnvio - antes).toBe(1);

  await context.setOffline(true);
  await aba(page, "Histórico");
  await expect(page.getByRole("listitem").filter({ hasText: `Açougue ${s}` })).toContainText("− R$ 3,00");
  await expect(page.getByRole("listitem").filter({ hasText: `Açougue ${s}` })).not.toContainText("não enviado");
});

/**
 * Roda antes do app quando o teste pede: troca o banco do aparelho pelo da versão anterior, com a
 * lista num bloco só em `respostas`. Os pedidos ao IndexedDB do mesmo banco correm na ordem, então
 * o app abre o banco depois de ele estar montado.
 */
function montarBancoAntigo() {
  const antigo = sessionStorage.getItem("banco-antigo");
  if (!antigo) return;
  sessionStorage.removeItem("banco-antigo");
  const respostas = JSON.parse(antigo) as [string, unknown][];
  indexedDB.deleteDatabase("financial-app-dados");
  const abertura = indexedDB.open("financial-app-dados", 1);
  abertura.onupgradeneeded = () => {
    abertura.result.createObjectStore("fila", { keyPath: "id" });
    const loja = abertura.result.createObjectStore("respostas");
    for (const [chave, valor] of respostas) loja.put(valor, chave);
  };
  abertura.onsuccess = () => abertura.result.close();
}

test("a lista guardada num bloco só pela versão anterior do app continua no aparelho sem internet", async ({ page, context }) => {
  await page.addInitScript(montarBancoAntigo);
  const { s, conta, mercado } = await prepararCasal(page);
  await lancar(page, { teclas: ["5", "00"], conta, categoria: mercado, descricao: `Do bloco ${s}` });
  await expect(page.getByRole("listitem").filter({ hasText: `Do bloco ${s}` })).not.toContainText("não enviado");
  await instalarCasca(page);

  // As respostas guardadas como a versão anterior as guardava: a lista inteira num bloco, com os outros cadastros.
  await page.evaluate(
    (lista) =>
      new Promise<void>((resolve, reject) => {
        const abertura = indexedDB.open("financial-app-dados");
        abertura.onerror = reject;
        abertura.onsuccess = () => {
          const banco = abertura.result;
          const nomes = [...banco.objectStoreNames];
          const transacao = banco.transaction(nomes, "readonly");
          const respostas = transacao.objectStore("respostas");
          const chaves = respostas.getAllKeys();
          const valores = respostas.getAll();
          const itens = nomes.includes("lancamentos") ? transacao.objectStore("lancamentos").getAll() : null;
          transacao.oncomplete = () => {
            banco.close();
            const pares = (chaves.result as string[]).map((chave, i) => [chave, valores.result[i]] as [string, { dados?: unknown }]);
            const comBloco = itens ? pares.map(([chave, valor]) => [chave, chave === lista ? { ...valor, dados: itens.result } : valor]) : pares;
            sessionStorage.setItem("banco-antigo", JSON.stringify(comBloco));
            resolve();
          };
        };
      }),
    LISTA,
  );

  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole("listitem").filter({ hasText: `Do bloco ${s}` })).toContainText("− R$ 5,00");
  await expect(page.getByRole("listitem").filter({ hasText: `Do bloco ${s}` })).not.toContainText("não enviado");
});
