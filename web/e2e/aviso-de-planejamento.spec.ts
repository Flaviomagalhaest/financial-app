import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";
import { digitar, lancar } from "./lancar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

const hoje = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
/** `2026-10-15` vira "out/26". */
const rotulo = (iso: string) => `${MESES[Number(iso.slice(5, 7)) - 1]}/${iso.slice(2, 4)}`;

/** Entra e devolve como cadastrar pela API, com o token da página: o planejamento ainda não tem tela (ticket 54). */
async function prepararCasal(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/hoje");
  await entrar(page);
  await expect(page.getByRole("link", { name: "+ Novo lançamento" })).toBeVisible();
  const pedido = page.waitForRequest((r) => r.url().includes("/api/") && !!r.headers().authorization);
  await page.reload();
  const headers = { authorization: (await pedido).headers().authorization };
  const criar = async (caminho: string, data: object) => {
    const resposta = await page.request.post(caminho, { headers, data });
    expect(resposta.ok(), await resposta.text()).toBe(true);
    return resposta.json();
  };
  const conta = `Corrente ${s}`;
  const { id: contaId } = await criar("/api/contas", { nome: conta, tipo: "corrente" });
  const categoria = async (nome: string, planejadoCentavos?: number, mes = hoje().slice(0, 7)) => {
    const { id } = await criar("/api/categorias", { nome: `${nome} ${s}`, tipo: "despesa" });
    if (planejadoCentavos) await criar(`/api/planejamento/${mes}/itens`, { id: randomUUID(), categoria_id: id, valor_centavos: planejadoCentavos });
    return { id, nome: `${nome} ${s}` };
  };
  const despesa = (campos: object) => criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", data: hoje(), conta_id: contaId, ...campos });
  return { s, headers, conta, contaId, criar, categoria, despesa };
}

async function novoLancamento(page: Page) {
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
}

const aviso = (page: Page) => page.getByRole("region", { name: "Aviso de planejamento" });

/** O realizado do item da categoria no planejamento do mês que o aparelho guardou (IndexedDB de `web/src/dados/armazem.ts`). */
function planejamentoGuardado(page: Page, mes: string, categoriaId: string) {
  return page.evaluate(
    ([mes, categoriaId]) =>
      new Promise<number | null>((resolve) => {
        const abertura = indexedDB.open("financial-app-dados");
        abertura.onsuccess = () => {
          const pedido = abertura.result.transaction("respostas").objectStore("respostas").get(`/api/planejamento/${mes}`);
          pedido.onsuccess = () => {
            abertura.result.close();
            const itens: { categoria_id: string; realizado_centavos: number }[] = pedido.result?.dados.itens ?? [];
            resolve(itens.find((i) => i.categoria_id === categoriaId)?.realizado_centavos ?? null);
          };
        };
        abertura.onerror = () => resolve(null);
      }),
    [mes, categoriaId],
  );
}

test("a cada toque, o aviso mostra o item antes e depois e quanto ainda dá para gastar ou quanto passa", async ({ page }) => {
  const { conta, categoria, despesa } = await prepararCasal(page);
  const mercado = await categoria("Mercado", 100000);
  const lazer = await categoria("Lazer");
  await despesa({ valor_centavos: 82000, categoria_ids: [mercado.id] });

  await novoLancamento(page);
  await page.getByRole("button", { name: conta, exact: true }).click();
  await expect(aviso(page)).toHaveCount(0);
  await page.getByRole("button", { name: mercado.nome, exact: true }).click();
  await expect(aviso(page)).toContainText(`${mercado.nome}: 82% do planejado de ${rotulo(hoje())}`);
  await expect(aviso(page)).toContainText("Ainda dá para gastar R$ 180,00");

  await digitar(page, "1", "5", "0", "0", "0");
  await expect(aviso(page)).toContainText(`${mercado.nome}: 82% → 97% do planejado de ${rotulo(hoje())}`);
  await expect(aviso(page)).toContainText("Ainda dá para gastar R$ 30,00");
  await digitar(page, "Apagar", "Apagar", "Apagar", "Apagar", "Apagar", "2", "3", "0", "0", "0");
  await expect(aviso(page)).toContainText(`${mercado.nome}: 82% → 105% do planejado de ${rotulo(hoje())}`);
  await expect(aviso(page)).toContainText("Passa R$ 50,00 do planejado");

  // Sem item em nenhuma das categorias, conta só no total do mês.
  await page.getByRole("button", { name: mercado.nome, exact: true }).click();
  await page.getByRole("button", { name: lazer.nome, exact: true }).click();
  await expect(aviso(page)).toContainText(`Nenhuma das categorias tem item no planejamento de ${rotulo(hoje())}, então conta só no total do mês.`);
});

test("com duas categorias com item, o aviso traz a última escolha para o conjunto, trocável com um toque", async ({ page }) => {
  const { s, headers, conta, categoria, despesa } = await prepararCasal(page);
  const restaurante = await categoria("Restaurante", 50000);
  const viagem = await categoria("Viagem", 200000);
  await despesa({ valor_centavos: 10000, categoria_ids: [restaurante.id, viagem.id], item_categoria_id: viagem.id });

  await novoLancamento(page);
  await digitar(page, "5", "0", "0", "0");
  await page.getByRole("button", { name: conta, exact: true }).click();
  await page.getByRole("button", { name: restaurante.nome, exact: true }).click();
  await page.getByRole("button", { name: viagem.nome, exact: true }).click();
  const ondeConta = aviso(page).getByRole("group", { name: "Conta no planejamento em:" });
  await expect(ondeConta.getByRole("button", { name: viagem.nome, exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(aviso(page)).toContainText(`${viagem.nome}: 5% → 8% do planejado`);

  await ondeConta.getByRole("button", { name: restaurante.nome, exact: true }).click();
  await expect(ondeConta.getByRole("button", { name: restaurante.nome, exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(aviso(page)).toContainText(`${restaurante.nome}: 0% → 10% do planejado`);
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(`Jantar ${s}`);
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("listitem").filter({ hasText: `Jantar ${s}` })).not.toContainText("não enviado");

  const lista: { descricao: string; item_categoria_id: string | null }[] = await (await page.request.get("/api/lancamentos", { headers })).json();
  expect(lista.find((l) => l.descricao === `Jantar ${s}`)?.item_categoria_id).toBe(restaurante.id);
});

test("a compra no cartão mostra a fatura em que cai e conta no planejamento do mês dela", async ({ page }) => {
  const { s, headers, criar, categoria } = await prepararCasal(page);
  // Fecha hoje: a compra de hoje já vai para a fatura seguinte.
  const cartao = await criar("/api/cartoes", { nome: `Visa ${s}`, dia_fechamento: Number(hoje().slice(8, 10)), dia_vencimento: 5 });
  // O servidor diz em que fatura cai a compra de hoje e quando ela fecha.
  const sonda = await categoria("Sonda");
  const compra = await criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos: 100, data: hoje(), conta_id: cartao.id, categoria_ids: [sonda.id] });
  await page.request.delete(`/api/lancamentos/${compra.id}?versao=${compra.versao}`, { headers });
  const faturas: { mes: string; fechamento: string }[] = await (await page.request.get(`/api/cartoes/${cartao.id}/faturas`, { headers })).json();
  const fatura = faturas.find((f) => f.mes === compra.mes)!;
  expect(compra.mes > hoje()).toBe(true);
  const farmacia = await categoria("Farmácia", 40000, compra.mes.slice(0, 7));

  await page.reload();
  await novoLancamento(page);
  await digitar(page, "1", "0", "0", "0", "0");
  await page.getByRole("button", { name: `Visa ${s}` }).click();
  await page.getByRole("button", { name: farmacia.nome, exact: true }).click();
  const [ano, mes] = [compra.mes.slice(0, 4), compra.mes.slice(5, 7)];
  const [, mesF, diaF] = fatura.fechamento.split("-");
  await expect(aviso(page)).toContainText(`Cai na fatura de ${mes}/${ano}, que fecha em ${diaF}/${mesF}, e conta em ${rotulo(compra.mes)}.`);
  await expect(aviso(page)).toContainText(`${farmacia.nome}: 0% → 25% do planejado de ${rotulo(compra.mes)}`);
});

test("sem internet, o aviso usa o planejamento guardado e já conta o não enviado", async ({ page, context }) => {
  const { s, conta, categoria, despesa } = await prepararCasal(page);
  const mercado = await categoria("Mercado", 100000);
  await despesa({ valor_centavos: 82000, categoria_ids: [mercado.id] });
  // Ao abrir, o app guarda o planejamento do mês. A resposta chega antes de ser gravada no
  // aparelho: espera a gravação (com o item já criado) antes de desligar a rede.
  await page.reload();
  await expect(page.getByRole("link", { name: "+ Novo lançamento" })).toBeVisible();
  await expect.poll(() => planejamentoGuardado(page, hoje().slice(0, 7), mercado.id)).toBe(82000);

  await context.setOffline(true);
  await lancar(page, { teclas: ["1", "0", "0", "0", "0"], conta, categoria: mercado.nome, descricao: `Feira ${s}` });
  await expect(page.getByRole("listitem").filter({ hasText: `Feira ${s}` })).toContainText("⏳ não enviado");

  await novoLancamento(page);
  await page.getByRole("button", { name: conta, exact: true }).click();
  await page.getByRole("button", { name: mercado.nome, exact: true }).click();
  await expect(aviso(page)).toContainText(`${mercado.nome}: 92% do planejado de ${rotulo(hoje())}`);
  await expect(aviso(page)).toContainText("Planejamento atualizado às");
  await digitar(page, "5", "0", "0", "0");
  await expect(aviso(page)).toContainText(`${mercado.nome}: 92% → 97% do planejado`);
  await context.setOffline(false);
});

test("sem escolha para o conjunto, nada fica marcado e o lançamento fica a escolher, também ao editar só o valor", async ({ page }) => {
  const { s, headers, conta, categoria } = await prepararCasal(page);
  const mercado = await categoria("Mercado", 100000);
  const casa = await categoria("Casa", 50000);

  await novoLancamento(page);
  await digitar(page, "5", "0", "0", "0");
  await page.getByRole("button", { name: conta, exact: true }).click();
  await page.getByRole("button", { name: mercado.nome, exact: true }).click();
  await page.getByRole("button", { name: casa.nome, exact: true }).click();
  const ondeConta = aviso(page).getByRole("group", { name: "Conta no planejamento em:" });
  await expect(ondeConta.getByRole("button", { name: mercado.nome })).toHaveAttribute("aria-pressed", "false");
  await expect(ondeConta.getByRole("button", { name: casa.nome })).toHaveAttribute("aria-pressed", "false");
  await expect(aviso(page)).toContainText('Sem escolha, ele fica em "a escolher" até alguém escolher o item.');
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(`Feira ${s}`);
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  const feira = page.getByRole("listitem").filter({ hasText: `Feira ${s}` });
  await expect(feira).not.toContainText("não enviado");

  await feira.getByRole("link", { name: `Editar Feira ${s}` }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 50,00");
  await digitar(page, "0");
  await expect(aviso(page)).toContainText('Sem escolha, ele fica em "a escolher"');
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(feira).toContainText("R$ 500,00");
  await expect(feira).not.toContainText("não enviado");

  const plano = await (await page.request.get(`/api/planejamento/${hoje().slice(0, 7)}`, { headers })).json();
  const lista: { id: string; descricao: string; item_categoria_id: string | null }[] = await (await page.request.get("/api/lancamentos", { headers })).json();
  const salvo = lista.find((l) => l.descricao === `Feira ${s}`)!;
  expect(salvo.item_categoria_id).toBeNull();
  expect(plano.a_escolher.map((a: { lancamento_id: string }) => a.lancamento_id)).toContain(salvo.id);
});

test("a transferência com categoria mostra o efeito no item de transferência do planejamento", async ({ page }) => {
  const { s, conta, criar } = await prepararCasal(page);
  await criar("/api/contas", { nome: `Reserva ${s}`, tipo: "poupanca" });
  const { id } = await criar("/api/categorias", { nome: `Guardar ${s}`, tipo: "transferencia" });
  await criar(`/api/planejamento/${hoje().slice(0, 7)}/itens`, { id: randomUUID(), categoria_id: id, valor_centavos: 100000 });

  await novoLancamento(page);
  await page.getByRole("group", { name: "Tipo" }).getByRole("button", { name: "Transferência" }).click();
  await expect(aviso(page)).toHaveCount(0);
  await digitar(page, "3", "0", "0", "0", "0");
  await page.getByRole("group", { name: "De" }).getByRole("button", { name: conta, exact: true }).click();
  await page.getByRole("group", { name: "Categoria (opcional)" }).getByRole("button", { name: `Guardar ${s}` }).click();
  await expect(aviso(page)).toContainText(`Guardar ${s}: 0% → 30% do planejado de ${rotulo(hoje())}`);
  await expect(aviso(page)).toContainText("Faltam R$ 700,00 para o planejado");
});

test("a compra não enviada num cartão arquivado conta pela fatura, não pelo mês da data", async ({ page, context }) => {
  const { s, headers, criar, categoria } = await prepararCasal(page);
  // Fecha hoje: a compra de hoje cai na fatura seguinte, que conta no mês seguinte.
  const fechamento = Number(hoje().slice(8, 10));
  const cartao = await criar("/api/cartoes", { nome: `Visa ${s}`, dia_fechamento: fechamento, dia_vencimento: 5 });
  const sonda = await categoria("Sonda");
  const compra = await criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos: 100, data: hoje(), conta_id: cartao.id, categoria_ids: [sonda.id] });
  await page.request.delete(`/api/lancamentos/${compra.id}?versao=${compra.versao}`, { headers });
  expect(compra.mes > hoje()).toBe(true);
  const farmacia = await categoria("Farmácia", 40000, compra.mes.slice(0, 7));
  const arquivado = await page.request.put(`/api/cartoes/${cartao.id}`, { headers, data: { nome: `Visa ${s}`, dia_fechamento: fechamento, dia_vencimento: 5, arquivado: true } });
  expect(arquivado.ok(), await arquivado.text()).toBe(true);
  // O cartão arquivado não sai em `GET /api/cartoes`, e a tela de lançar já não o oferece.
  const ativos: { id: string }[] = await (await page.request.get("/api/cartoes", { headers })).json();
  expect(ativos.map((c) => c.id)).not.toContain(cartao.id);

  // A compra que ficou na fila antes do arquivamento, posta direto no aparelho: sem tentativa de envio.
  await page.reload();
  await expect(page.getByRole("link", { name: "+ Novo lançamento" })).toBeVisible();
  const id = randomUUID();
  await page.evaluate(
    ([id, contaId, categoriaId, descricao, data]) =>
      new Promise<void>((resolve) => {
        const abertura = indexedDB.open("financial-app-dados");
        abertura.onsuccess = () => {
          const transacao = abertura.result.transaction("fila", "readwrite");
          const lancamento = { id, tipo: "despesa", valor_centavos: 10000, data, descricao, conta_id: contaId, categoria_ids: [categoriaId], pessoa: null, fatura_mes: null, item_categoria_id: null, tags: [] };
          transacao.objectStore("fila").put({ id, acao: "criar", lancamento, desde: Date.now(), feitoEm: Date.now(), revisao: 1 });
          transacao.oncomplete = () => {
            abertura.result.close();
            resolve();
          };
        };
      }),
    [id, cartao.id, farmacia.id, `Remédio ${s}`, hoje()],
  );
  await expect.poll(() => planejamentoGuardado(page, compra.mes.slice(0, 7), farmacia.id)).toBe(0);

  // Sem internet, o envio não sai e nada recarrega do servidor: o aviso lê o que o aparelho guardou.
  await context.setOffline(true);
  await page.reload();
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Histórico" }).click();
  const linha = page.getByRole("listitem").filter({ hasText: `Remédio ${s}` });
  await expect(linha).toContainText("⏳ não enviado");
  await linha.getByRole("link", { name: new RegExp(`^(Editar|Corrigir) Remédio ${s}$`) }).click();
  await expect(aviso(page)).toContainText(`Cai na fatura de ${compra.mes.slice(5, 7)}/${compra.mes.slice(0, 4)}`);
  await expect(aviso(page)).toContainText(`${farmacia.nome}: 25% do planejado de ${rotulo(compra.mes)}`);
  await context.setOffline(false);
});

test("o criar enviado sem resposta e já lido pelo planejamento conta uma vez só no aviso", async ({ page }) => {
  const { s, headers, conta, categoria } = await prepararCasal(page);
  const mercado = await categoria("Mercado", 100000);
  // O servidor grava o lançamento, mas a resposta não chega; depois nenhum envio passa.
  let perdidas = 0;
  await page.route("**/api/lancamentos/lote", async (rota) => {
    if (perdidas++ === 0) await rota.fetch();
    await rota.abort("connectionreset");
  });
  await lancar(page, { teclas: ["1", "0", "0", "0", "0"], conta, categoria: mercado.nome, descricao: `Feira ${s}` });
  await expect.poll(() => perdidas).toBeGreaterThan(0);
  // O servidor gravou: o planejamento dele já conta os R$ 100,00.
  const plano = await (await page.request.get(`/api/planejamento/${hoje().slice(0, 7)}`, { headers })).json();
  expect(plano.itens.find((i: { categoria_id: string }) => i.categoria_id === mercado.id).realizado_centavos).toBe(10000);
  // A fila guarda a hora do envio e a versão enviada (`tentadoEm`, `base`).
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          new Promise<boolean>((resolve) => {
            const abertura = indexedDB.open("financial-app-dados");
            abertura.onsuccess = () => {
              const todos = abertura.result.transaction("fila").objectStore("fila").getAll();
              todos.onsuccess = () => {
                abertura.result.close();
                resolve((todos.result as { tentadoEm?: number; talvezNoServidor?: number }[]).some((i) => i.tentadoEm && i.talvezNoServidor !== undefined));
              };
            };
          }),
      ),
    )
    .toBe(true);

  // O planejamento lido agora, depois do envio, já traz os R$ 100,00, mas a lista de lançamentos
  // ainda é a de antes dele (as duas leituras não chegam juntas): a fila não soma de novo.
  await page.route("**/api/lancamentos", (rota) => (rota.request().method() === "GET" ? rota.fulfill({ json: [] }) : rota.continue()));
  await page.reload();
  await novoLancamento(page);
  await page.getByRole("button", { name: conta, exact: true }).click();
  await page.getByRole("button", { name: mercado.nome, exact: true }).click();
  await digitar(page, "5", "0", "0", "0");
  await expect(aviso(page)).toContainText(`${mercado.nome}: 10% → 15% do planejado`);
});
