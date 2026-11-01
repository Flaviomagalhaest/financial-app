import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { digitar } from "./lancar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

const hoje = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());

/** Entra e prepara pela API um cartão, três categorias e o item de Roupa no planejamento do mês da fatura de hoje. */
async function preparar(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const nomes = { cartao: `Master ${s}`, roupa: `Roupa ${s}`, fone: `Eletrônico ${s}`, casa: `Casa ${s}`, compra: `Mercado Livre ${s}` };
  await page.goto("/#/historico");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  const api = await apiDaPagina(page);
  // Fecha no dia 28: a compra de hoje cai na fatura deste mês ou do seguinte, e o aviso diz qual.
  const cartao = await api.criar("/api/cartoes", { nome: nomes.cartao, dia_fechamento: 28, dia_vencimento: 5 });
  const roupa = await api.criar("/api/categorias", { nome: nomes.roupa, tipo: "despesa" });
  await api.criar("/api/categorias", { nome: nomes.fone, tipo: "despesa" });
  await api.criar("/api/categorias", { nome: nomes.casa, tipo: "despesa" });
  const dia = Number(hoje().slice(8, 10));
  const mes = new Date(`${hoje().slice(0, 7)}-15T12:00:00Z`);
  if (dia >= 28) mes.setUTCMonth(mes.getUTCMonth() + 1);
  const mesDaFatura = mes.toISOString().slice(0, 7);
  await api.criar(`/api/planejamento/${mesDaFatura}/itens`, { id: crypto.randomUUID(), categoria_id: roupa.id, valor_centavos: 100000 });
  await page.reload();
  return { s, api, cartao, nomes, mesDaFatura };
}

const parte = (page: Page, n: number) => page.getByRole("group", { name: `Parte ${n}`, exact: true });

test("divide a compra em partes ao lançar: cada parte com a classificação e o aviso dela, e a compra numa linha só que abre as partes", async ({ page }) => {
  const { nomes, cartao, mesDaFatura } = await preparar(page);
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();

  // R$ 1.000,00 no cartão, com a descrição da compra.
  await digitar(page, "1", "00", "00", "0");
  await page.getByRole("button", { name: nomes.cartao }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição", { exact: true }).fill(nomes.compra);
  await page.getByRole("button", { name: "Pronto" }).click();

  // Duas partes: a primeira se digita e a última fica com o que falta da compra.
  await page.getByRole("button", { name: "Dividir em partes" }).click();
  await parte(page, 1).getByLabel("Descrição da parte").fill("Vestido");
  await parte(page, 1).getByLabel("Valor da parte").fill("500,00");
  await parte(page, 1).getByRole("button", { name: nomes.roupa }).click();
  await parte(page, 1).getByRole("group", { name: "Pessoa de Vestido" }).getByRole("button", { name: "Fulana" }).click();
  await expect(parte(page, 2).getByLabel("Valor de Parte 2")).toContainText("R$ 500,00");

  // Uma terceira: a segunda fica com o valor que tinha, e se acerta para R$ 250,00.
  await page.getByRole("button", { name: "+ Parte" }).click();
  await parte(page, 2).getByLabel("Descrição da parte").fill("Fone");
  await parte(page, 2).getByLabel("Valor da parte").fill("250,00");
  await parte(page, 2).getByRole("button", { name: nomes.fone }).click();
  await parte(page, 3).getByLabel("Descrição da parte").fill("Cortina");
  await parte(page, 3).getByRole("button", { name: nomes.casa }).click();
  await expect(parte(page, 3).getByLabel("Valor de Cortina")).toContainText("R$ 250,00");

  // O aviso de planejamento é por parte: o Vestido enche metade do item de Roupa.
  await expect(parte(page, 1).getByTestId("efeito-no-item")).toContainText(`${nomes.roupa}: 0% → 50%`);
  await expect(parte(page, 3).getByText(/Nenhuma das categorias tem item/)).toBeVisible();

  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  // No Histórico, uma linha só com o valor da compra, que abre as partes.
  const linha = page.getByRole("listitem").filter({ hasText: nomes.compra }).first();
  await expect(linha).toContainText("− R$ 1.000,00");
  await expect(linha).not.toContainText("não enviado");
  await linha.getByText("3 partes").click();
  const partes = linha.getByRole("list", { name: `Partes de ${nomes.compra}` });
  await expect(partes.getByRole("listitem")).toHaveCount(3);
  await expect(partes.getByRole("listitem").nth(0)).toContainText("Vestido");
  await expect(partes.getByRole("listitem").nth(0)).toContainText("R$ 500,00");
  await expect(partes.getByRole("listitem").nth(0)).toContainText(`${nomes.roupa} · Fulana`);

  // Na fatura também é uma linha; o filtro pela categoria mostra só a parte que bate, com o valor dela.
  await page.goto(`/#/cartoes/${cartao.id}/${mesDaFatura}-01`);
  await expect(page.getByRole("heading", { name: /^Fatura de/ })).toBeVisible();
  const naFatura = page.getByRole("listitem").filter({ hasText: nomes.compra }).first();
  await expect(naFatura).toContainText("− R$ 1.000,00");
  await page.getByLabel("Categoria").selectOption({ label: nomes.casa });
  await expect(page.getByText("Filtrado: R$ 250,00")).toBeVisible();
  await expect(naFatura).toContainText("− R$ 250,00");
  await naFatura.getByText("1 de 3 partes").click();
  await expect(naFatura.getByRole("list", { name: `Partes de ${nomes.compra}` }).getByRole("listitem")).toHaveCount(1);
  await expect(naFatura).toContainText("Cortina");

  // O planejamento do mês conta só o Vestido no item de Roupa.
  const plano = await (await apiDaPagina(page)).ler(`/api/planejamento/${mesDaFatura}`);
  expect(plano.itens[0].realizado_centavos + plano.itens[0].previsto_centavos).toBe(50000);
});

test("tirar a penúltima parte devolve a classificação dela à compra", async ({ page }) => {
  const { api, cartao, nomes } = await preparar(page);
  const categorias = await api.ler("/api/categorias");
  const id = (nome: string) => categorias.find((c: { nome: string }) => c.nome === nome).id;
  const compra = await api.criar("/api/lancamentos", {
    id: crypto.randomUUID(),
    tipo: "despesa",
    valor_centavos: 30000,
    data: hoje(),
    descricao: nomes.compra,
    conta_id: cartao.id,
    categoria_ids: [],
    tags: [],
    partes: [
      { id: crypto.randomUUID(), descricao: "Vestido", valor_centavos: 20000, categoria_ids: [id(nomes.roupa)], tags: [], pessoa: "sub-esposa" },
      { id: crypto.randomUUID(), descricao: "Cortina", valor_centavos: 10000, categoria_ids: [id(nomes.casa)], tags: [`sala ${nomes.compra}`] },
    ],
  });
  await page.reload();

  await page.getByRole("link", { name: `Editar ${nomes.compra}` }).click();
  await expect(parte(page, 2).getByLabel("Valor de Cortina")).toContainText("R$ 100,00");
  await parte(page, 1).getByRole("button", { name: "Tirar Vestido" }).click();

  // A compra volta a ser uma, com a categoria, a tag e a pessoa da Cortina.
  await expect(page.getByRole("region", { name: "Partes da compra" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: nomes.casa })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  const linha = page.getByRole("listitem").filter({ hasText: nomes.compra }).first();
  await expect(linha).toContainText(nomes.casa);
  await expect(linha).toContainText(`#sala ${nomes.compra}`);
  await expect(linha).not.toContainText("não enviado");
  await expect(linha.getByText(/partes$/)).toHaveCount(0);
  const [gravada] = (await api.ler("/api/lancamentos")).filter((l: { id: string }) => l.id === compra.id);
  expect(gravada.partes).toEqual([]);
  expect(gravada.valor_centavos).toBe(30000);
});

test("sem internet, a compra com partes entra na fila como um pedido só e sobe quando a rede volta", async ({ page, context }) => {
  const { nomes } = await preparar(page);
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  // A rede cai com o cadastro já guardado no aparelho.
  await expect(page.getByRole("button", { name: nomes.casa })).toBeVisible();
  await context.setOffline(true);
  await digitar(page, "9", "00");
  await page.getByRole("button", { name: nomes.cartao }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição", { exact: true }).fill(nomes.compra);
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Dividir em partes" }).click();
  await parte(page, 1).getByLabel("Valor da parte").fill("6,00");
  await parte(page, 1).getByRole("button", { name: nomes.roupa }).click();
  await parte(page, 2).getByRole("button", { name: nomes.casa }).click();
  await page.getByRole("button", { name: "Salvar" }).click();

  const linha = page.getByRole("listitem").filter({ hasText: nomes.compra }).first();
  await expect(linha).toContainText("⏳ não enviado");
  await expect(linha).toContainText("2 partes");

  await context.setOffline(false);
  await expect(linha).not.toContainText("não enviado");
  await expect(linha).toContainText("− R$ 9,00");
});

test("no conflito, as partes são um campo só: quem decide escolhe a lista inteira de um lado", async ({ page, context, browser }) => {
  const { api, cartao, nomes } = await preparar(page);
  const categorias = await api.ler("/api/categorias");
  const id = (nome: string) => categorias.find((c: { nome: string }) => c.nome === nome).id;
  await api.criar("/api/lancamentos", {
    id: crypto.randomUUID(),
    tipo: "despesa",
    valor_centavos: 30000,
    data: hoje(),
    descricao: nomes.compra,
    conta_id: cartao.id,
    categoria_ids: [],
    tags: [],
    partes: [
      { id: crypto.randomUUID(), descricao: "Vestido", valor_centavos: 20000, categoria_ids: [id(nomes.roupa)], tags: [] },
      { id: crypto.randomUUID(), descricao: "Cortina", valor_centavos: 10000, categoria_ids: [id(nomes.casa)], tags: [] },
    ],
  });
  await page.reload();
  const minha = page.getByRole("listitem").filter({ hasText: nomes.compra }).first();
  await expect(minha).toContainText("2 partes");

  const contextoDela = await browser.newContext({ timezoneId: "America/Sao_Paulo" });
  const dela = await contextoDela.newPage();
  await dela.goto("/#/historico");
  await entrar(dela, "esposa@teste.com");
  const naDela = dela.getByRole("listitem").filter({ hasText: nomes.compra }).first();
  await expect(naDela).toContainText("2 partes");

  // Sem internet, eu renomeio o Vestido; ela, com internet, renomeia a Cortina.
  await context.setOffline(true);
  await minha.getByRole("link", { name: `Editar ${nomes.compra}` }).click();
  await parte(page, 1).getByLabel("Descrição da parte").fill("Vestido azul");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(minha).toContainText("⏳ não enviado");

  await naDela.getByRole("link", { name: `Editar ${nomes.compra}` }).click();
  await parte(dela, 2).getByLabel("Descrição da parte").fill("Cortina da sala");
  await dela.getByRole("button", { name: "Salvar" }).click();
  await expect(naDela).not.toContainText("não enviado");
  await expect
    .poll(async () => (await api.ler("/api/lancamentos")).find((l: { descricao: string }) => l.descricao === nomes.compra)?.partes[1].descricao)
    .toBe("Cortina da sala");

  await context.setOffline(false);
  await expect(minha).toContainText("⚠ conflito: sua mudança espera decisão");
  await minha.getByRole("link", { name: `Decidir ${nomes.compra}` }).click();
  const partes = page.getByRole("group", { name: "Partes" });
  await expect(page.getByRole("group", { name: /^(Categorias|Tags|Pessoa)$/ })).toHaveCount(0);
  await expect(partes.getByRole("button", { name: /^O seu: Vestido azul R\$ 200,00.*Cortina R\$ 100,00/ })).toBeVisible();
  await partes.getByRole("button", { name: /^O de Fulana.*Cortina da sala/ }).click();
  await page.getByRole("button", { name: "Salvar a decisão" }).click();

  // A lista dela fica inteira: o Vestido volta ao nome de antes.
  await minha.getByText("2 partes").click();
  await expect(minha.getByRole("list", { name: `Partes de ${nomes.compra}` })).toContainText("Cortina da sala");
  await expect(minha.getByRole("list", { name: `Partes de ${nomes.compra}` })).not.toContainText("Vestido azul");
  await expect(minha).not.toContainText("conflito");
  await contextoDela.close();
});
