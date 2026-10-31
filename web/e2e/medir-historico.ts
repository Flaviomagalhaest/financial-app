// Mede o Histórico com o volume do banco (ticket 123): o tempo até a tela mostrar um lançamento
// novo, separando a leitura da lista (`GET /api/lancamentos`), as gravações e leituras dela no
// IndexedDB e o render, num celular mais lento simulado (CPU throttling do Chromium).
//
// Precisa do Cognito falso, da API e do app no ar, como no README ("Como rodar"; o app pelo
// `npm run build && npm run preview`, porta 4173). Não é teste: não entra no `playwright test`.
// O volume vem do gerador do ticket 112, num banco só para isso (ele apaga o schema `public`):
//   (cd backend && DATABASE_URL=<banco de medida> uv run python -c \
//     "import os, psycopg; from medir_busca import gerar; gerar(psycopg.connect(os.environ['DATABASE_URL'], autocommit=True), 10600, 80)")
// (10.600 avulsos e 80 parcelamentos de 5 dão 11 mil lançamentos); reinicie a API depois.
// A espera do lançamento novo é um MutationObserver na página, não o `getByRole` do Playwright,
// que percorre os milhares de itens da lista e pesa ele mesmo na medida.
//
// Uso: node e2e/medir-historico.ts [lentidão da CPU, 4] [rodadas, 3]   (URL_DO_APP troca a porta)
import { randomUUID } from "node:crypto";
import { chromium, type Page } from "@playwright/test";

const URL_DO_APP = process.env.URL_DO_APP ?? "http://127.0.0.1:4173";
const lentidao = Number(process.argv[2] ?? 4);
const rodadas = Number(process.argv[3] ?? 3);
const LISTA = "/api/lancamentos";

/** Roda na página antes do app: anota cada leitura e gravação da lista no IndexedDB e as tarefas longas. */
function instrumentar(lista: string) {
  type Marca = { tipo: string; inicio: number; fim?: number; sincrono?: number; tamanho?: number };
  const marcas: Marca[] = [];
  (window as unknown as { __medidas: Marca[] }).__medidas = marcas;
  const agora = () => performance.now();
  const put = IDBObjectStore.prototype.put;
  IDBObjectStore.prototype.put = function (this: IDBObjectStore, valor: unknown, chave?: IDBValidKey) {
    if (chave !== lista) return put.call(this, valor, chave);
    const marca: Marca = { tipo: "gravar", inicio: agora() };
    const pedido = put.call(this, valor, chave);
    marca.sincrono = agora() - marca.inicio; // a cópia estruturada roda aqui, na thread da tela
    this.transaction.addEventListener("complete", () => (marca.fim = agora()));
    marcas.push(marca);
    return pedido;
  };
  const get = IDBObjectStore.prototype.get;
  IDBObjectStore.prototype.get = function (this: IDBObjectStore, chave: IDBValidKey | IDBKeyRange) {
    const pedido = get.call(this, chave);
    if (chave !== lista) return pedido;
    const marca: Marca = { tipo: "ler guardada", inicio: agora() };
    pedido.addEventListener("success", () => (marca.fim = agora()));
    marcas.push(marca);
    return pedido;
  };
  const json = Response.prototype.json;
  Response.prototype.json = async function (this: Response) {
    if (!new URL(this.url).pathname.endsWith(lista)) return json.call(this);
    const marca: Marca = { tipo: "json", inicio: agora() };
    const dados = await json.call(this);
    marca.fim = agora();
    marca.tamanho = Array.isArray(dados) ? dados.length : undefined;
    marcas.push(marca);
    return dados;
  };
  // Quando o lançamento esperado entra na tela, sem varrer a página.
  const esperado = sessionStorage.getItem("medir-esperado");
  if (esperado)
    new MutationObserver((mudancas, observador) => {
      for (const m of mudancas)
        for (const n of m.addedNodes)
          if (n.textContent?.includes(esperado)) {
            const visto = agora();
            requestAnimationFrame(() => setTimeout(() => ((window as unknown as { __mostrado: number }).__mostrado = visto)));
            return observador.disconnect();
          }
    }).observe(document, { childList: true, subtree: true });
  new PerformanceObserver((l) => {
    for (const e of l.getEntries()) marcas.push({ tipo: "tarefa longa", inicio: e.startTime, fim: e.startTime + e.duration });
  }).observe({ type: "longtask", buffered: true });
}

type Medida = {
  ateMostrar: number;
  leituras: { inicio: number; resposta: number; fim: number; bytes: number }[];
  /** As outras leituras da API na mesma abertura, que disputam o servidor com a lista. */
  outras: { caminho: string; inicio: number; resposta: number; fim: number; bytes: number }[];
  marcas: { tipo: string; inicio: number; fim?: number; sincrono?: number; tamanho?: number }[];
  itens: number;
};

async function medir(page: Page, descricao: string, acao: () => Promise<unknown>): Promise<Medida> {
  await page.evaluate((d) => sessionStorage.setItem("medir-esperado", d), descricao);
  await acao();
  const ateMostrar = (await (
    await page.waitForFunction(() => (window as unknown as { __mostrado?: number }).__mostrado, null, { timeout: 300_000, polling: 250 })
  ).jsonValue()) as number;
  // Espera as leituras e gravações que ainda estão no caminho para medir todas.
  await page.waitForTimeout(3000);
  return page.evaluate((lista) => {
    const leituras = (performance.getEntriesByType("resource") as PerformanceResourceTiming[])
      .filter((r) => new URL(r.name).pathname === lista)
      .map((r) => ({ inicio: r.startTime, resposta: r.responseStart, fim: r.responseEnd, bytes: r.encodedBodySize }));
    const marcas = (window as unknown as { __medidas: Medida["marcas"] }).__medidas;
    const outras = (performance.getEntriesByType("resource") as PerformanceResourceTiming[])
      .filter((r) => new URL(r.name).pathname.startsWith("/api/") && new URL(r.name).pathname !== lista)
      .map((r) => ({ caminho: new URL(r.name).pathname, inicio: r.startTime, resposta: r.responseStart, fim: r.responseEnd, bytes: r.encodedBodySize }));
    return { ateMostrar: 0, leituras, outras, marcas, itens: document.querySelectorAll("li").length };
  }, LISTA).then((m) => ({ ...m, ateMostrar }));
}

const ms = (n: number) => `${Math.round(n)} ms`;
const soma = (ns: number[]) => ns.reduce((a, b) => a + b, 0);

function relatar(nome: string, m: Medida) {
  const tipo = (t: string) => m.marcas.filter((x) => x.tipo === t);
  const gravacoes = tipo("gravar");
  const longas = tipo("tarefa longa").filter((x) => x.inicio <= m.ateMostrar);
  console.log(`\n## ${nome}: ${ms(m.ateMostrar)} até mostrar o lançamento novo (${m.itens} itens de lista na tela)`);
  console.log(`  GET ${LISTA}: ${m.leituras.length}x; ${m.leituras.map((l) => `servidor ${ms(l.resposta - l.inicio)} + download ${ms(l.fim - l.resposta)}, ${Math.round(l.bytes / 1024)} KB`).join("; ")}`);
  console.log(`  outras leituras da API: ${m.outras.filter((o) => o.inicio <= m.ateMostrar).map((o) => `${o.caminho} ${ms(o.inicio)}→${ms(o.fim)}`).join(", ")}`);
  console.log(`  JSON da lista: ${tipo("json").map((x) => `${ms(x.fim! - x.inicio)} (${x.tamanho} lançamentos)`).join(", ")}`);
  console.log(`  gravações no IndexedDB: ${gravacoes.length}x; cópia na thread da tela ${gravacoes.map((g) => ms(g.sincrono!)).join(", ")}; até gravar ${gravacoes.map((g) => ms((g.fim ?? NaN) - g.inicio)).join(", ")}`);
  console.log(`  leituras da guardada: ${tipo("ler guardada").length}x; ${tipo("ler guardada").map((x) => ms((x.fim ?? NaN) - x.inicio)).join(", ")}`);
  const quando = (x: { inicio: number; fim?: number }) => `${ms(x.inicio)}→${ms(x.fim ?? NaN)}`;
  console.log(`  linha do tempo (desde o início da página): GET ${m.leituras.map((l) => `${ms(l.inicio)}→${ms(l.fim)}`).join(", ")}; JSON ${tipo("json").map(quando).join(", ")}; gravar ${gravacoes.map(quando).join(", ")}; tarefas longas ${longas.map(quando).join(", ")}`);
  console.log(`  tarefas longas até mostrar: ${longas.length}, somando ${ms(soma(longas.map((x) => x.fim! - x.inicio)))}; a maior ${ms(Math.max(0, ...longas.map((x) => x.fim! - x.inicio)))}`);
}

const navegador = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
const contexto = await navegador.newContext({ baseURL: URL_DO_APP, timezoneId: "America/Sao_Paulo" });
await contexto.addInitScript(instrumentar, LISTA);
const page = await contexto.newPage();
const cdp = await contexto.newCDPSession(page);
await page.goto("/#/historico");
// Como `entrar` e `apiDaPagina` (e2e/), que o node não importa sem a extensão no caminho.
await page.getByLabel("E-mail").fill("flavio@teste.com");
await page.getByLabel("Senha").fill("uma senha qualquer");
await page.getByRole("button", { name: "Entrar" }).click();
await page.getByRole("button", { name: "Sair" }).waitFor();
const comToken = page.waitForRequest((r) => r.url().includes("/api/") && !!r.headers().authorization);
await page.reload();
const headers = { authorization: (await comToken).headers().authorization };
const criar = async (caminho: string, data: object) => (await page.request.post(caminho, { headers, data })).json();
const ler = async (caminho: string) => (await page.request.get(caminho, { headers })).json();
const [conta] = await ler("/api/contas");
const [categoria] = (await ler("/api/categorias")).filter((c: { tipo: string }) => c.tipo === "despesa");
const noServidor: number[] = [];
let total = 0;
let bytes = 0;
for (let i = 0; i < 3; i++) {
  const inicio = performance.now();
  const resposta = await page.request.get(LISTA, { headers });
  bytes = (await resposta.body()).length;
  noServidor.push(performance.now() - inicio);
  total = (await resposta.json()).length;
}
console.log(`# Histórico com ${total} lançamentos, CPU ${lentidao}x mais lenta, ${rodadas} rodadas`);
console.log(`GET ${LISTA} fora do navegador: ${noServidor.map(ms).join(", ")}; ${(bytes / 1024 / 1024).toFixed(1)} MB (${Math.round(bytes / total)} bytes por lançamento)`);
await cdp.send("Emulation.setCPUThrottlingRate", { rate: lentidao });

const hoje = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
const novo = (descricao: string) =>
  criar(LISTA, { id: randomUUID(), tipo: "despesa", valor_centavos: 123, data: hoje, descricao, conta_id: conta.id, categoria_ids: [categoria.id], tags: [] });

/** O tempo da thread da tela por tipo de trabalho (JS, estilo, layout, pintura, GC), do trace do Chromium. */
function resumirTrace(trace: { traceEvents: { name: string; ph: string; dur?: number; ts: number; pid: number; tid: number; args?: { name?: string } }[] }, ate: number) {
  const eventos = trace.traceEvents;
  const principal = eventos.find((e) => e.name === "thread_name" && e.args?.name === "CrRendererMain" && eventos.some((x) => x.pid === e.pid && x.name === "Layout"));
  if (!principal) return "sem a thread da tela no trace";
  const daTela = eventos.filter((e) => e.pid === principal.pid && e.tid === principal.tid && e.ph === "X" && e.dur);
  const inicio = Math.min(...daTela.filter((e) => e.name === "RunTask").map((e) => e.ts));
  const grupos: Record<string, string[]> = {
    JS: ["FunctionCall", "EvaluateScript", "v8.compile", "TimerFire", "FireAnimationFrame", "EventDispatch"],
    estilo: ["UpdateLayoutTree"],
    layout: ["Layout"],
    pintura: ["PrePaint", "Paint", "Layerize", "CompositeLayers"],
    GC: ["MajorGC", "MinorGC", "V8.GC_MARK_COMPACTOR", "BlinkGC.AtomicPhase"],
  };
  const somas = Object.entries(grupos).map(([nome, nomes]) => {
    const total = daTela.filter((e) => nomes.includes(e.name) && e.ts - inicio <= ate * 1000).reduce((a, e) => a + e.dur!, 0);
    return `${nome} ${ms(total / 1000)}`;
  });
  const ocupada = daTela.filter((e) => e.name === "RunTask" && e.ts - inicio <= ate * 1000).reduce((a, e) => a + e.dur!, 0);
  return `thread da tela ocupada ${ms(ocupada / 1000)} até mostrar: ${somas.join(", ")} (JS inclui o GC dentro dele)`;
}

const resultados: number[] = [];
for (let r = 1; r <= rodadas; r++) {
  // Como os testes que falharam: o lançamento entra pela API e a tela recarrega com a lista já guardada.
  const descricao = `Medida ${Date.now()}`;
  await navegador.startTracing(page, { categories: ["devtools.timeline", "disabled-by-default-devtools.timeline", "v8", "blink.user_timing"] });
  const m = await medir(page, descricao, async () => {
    await novo(descricao);
    await page.reload();
  });
  const trace = JSON.parse((await navegador.stopTracing()).toString());
  relatar(`recarregar com a lista guardada, rodada ${r}`, m);
  console.log(`  ${resumirTrace(trace, m.ateMostrar)}`);
  resultados.push(m.ateMostrar);
}
console.log(`\nmediana até mostrar: ${ms(resultados.sort((a, b) => a - b)[Math.floor(resultados.length / 2)])}`);
await navegador.close();
