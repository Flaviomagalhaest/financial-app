import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";

test.use({ timezoneId: "America/Sao_Paulo" });

type Api = Awaited<ReturnType<typeof apiDaPagina>>;

/**
 * Os testes dividem o banco: um ano antigo em que os meses usados ainda estão vazios (sem
 * lançamento nem item) deixa os totais só com o que o teste lança.
 */
async function anoVazio(api: Api, meses: (ano: number) => string[]): Promise<number> {
  for (;;) {
    const ano = 1100 + Math.floor(Math.random() * 800);
    const leituras = await Promise.all(meses(ano).map((mes) => api.ler(`/api/meses/${mes}`)));
    const vazio = (l: { despesas: { realizado_centavos: number; previsto_centavos: number }; receitas: { realizado_centavos: number; previsto_centavos: number }; planejamento: { itens: unknown[] } }) =>
      !l.despesas.realizado_centavos && !l.despesas.previsto_centavos && !l.receitas.realizado_centavos && !l.receitas.previsto_centavos && !l.planejamento.itens.length;
    if (leituras.every(vazio)) return ano;
  }
}

test("a aba Mês navega até um mês passado, lê o fechamento, compara, abre o ranking e escolhe o item", async ({ page, context }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/mes");
  await entrar(page);
  await expect(page.getByText("mês atual")).toBeVisible();
  await expect(page.getByRole("region", { name: "Despesas × planejamento" })).toBeVisible();

  const api = await apiDaPagina(page);
  const { criar } = api;
  const ano = await anoVazio(api, (a) => [`${a}-03`, `${a}-02`, `${a - 1}-03`]);
  const [marco, fevereiro, marcoDoAnoPassado] = [`${ano}-03`, `${ano}-02`, `${ano - 1}-03`];
  const conta = await criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const categoria = async (nome: string, tipo = "despesa") => (await criar("/api/categorias", { nome: `${nome} ${s}`, tipo })).id as string;
  const [mercado, restaurante, viagem, salario] = [await categoria("Mercado"), await categoria("Restaurante"), await categoria("Viagem"), await categoria("Salário", "receita")];
  const lancar = (centavos: number, data: string, categorias: string[], extra: object = {}) =>
    criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos: centavos, data, descricao: "", conta_id: conta.id, categoria_ids: categorias, tags: [], ...extra });
  const planejar = (mes: string, categoriaId: string, centavos: number) => criar(`/api/planejamento/${mes}/itens`, { id: randomUUID(), categoria_id: categoriaId, valor_centavos: centavos });

  await planejar(marco, mercado, 50000);
  await planejar(marco, restaurante, 30000);
  await planejar(marco, viagem, 100000);
  await lancar(400000, `${marco}-05`, [salario], { tipo: "receita", descricao: `Salário ${s}` });
  await lancar(60000, `${marco}-06`, [mercado], { descricao: `Feira ${s}`, tags: [`feira ${s}`], pessoa: "sub-esposa" });
  await lancar(20000, `${marco}-07`, [restaurante, viagem], { descricao: `Jantar ${s}` });
  // O previsto que ninguém confirmou fica fora do fechamento.
  await lancar(9900, `${marco}-20`, [salario], { tipo: "receita", situacao: "previsto" });
  await lancar(50000, `${fevereiro}-06`, [mercado]);
  await lancar(100000, `${marcoDoAnoPassado}-06`, [mercado]);

  await page.goto(`/#/mes/${fevereiro}`);
  await page.getByRole("link", { name: "Próximo mês" }).click();
  await expect(page.getByRole("heading", { name: `Março de ${ano}` })).toBeVisible();
  const fechamento = page.getByRole("region", { name: "Fechamento do mês" });
  await expect(fechamento).toContainText(`Março de ${ano} fechou com R$ 4.000,00 de receitas e R$ 800,00 de despesas. Sobraram R$ 3.200,00 (80% das receitas).`);
  await expect(fechamento).toContainText(`Passou do planejado em Mercado ${s} (+R$ 100,00); 2 de 3 itens ficaram dentro.`);
  await expect(fechamento).toContainText(`Em relação a fevereiro de ${ano}, as despesas subiram 60%. Em relação a março de ${ano - 1}, as despesas caíram 20%.`);
  await expect(fechamento).toContainText("1 previsto ficou sem confirmar e não entra nas contas acima.");

  // Comparação: o total conta o jantar uma vez; tocar na linha mostra os valores antigos.
  const comparacao = page.getByRole("region", { name: "Comparação" });
  await expect(comparacao.getByRole("row").filter({ hasText: "Total de despesas" })).toContainText("R$ 800,00");
  await comparacao.getByRole("button", { name: `Mercado ${s}` }).click();
  await expect(comparacao).toContainText(`fevereiro de ${ano}: R$ 500,00 · março de ${ano - 1}: R$ 1.000,00`);

  // Ranking por tag abre os lançamentos numa folha.
  const ranking = page.getByRole("region", { name: "Ranking" });
  await ranking.getByRole("button", { name: "Tag", exact: true }).click();
  await ranking.getByRole("button", { name: new RegExp(`#feira ${s}`) }).click();
  const folha = page.getByRole("dialog", { name: `#feira ${s}` });
  await expect(folha).toContainText(`Feira ${s}`);
  await folha.getByRole("button", { name: "Fechar" }).click();
  await ranking.getByRole("button", { name: "Pessoa", exact: true }).click();
  await expect(ranking.getByRole("listitem")).toHaveCount(2);
  await expect(ranking.getByRole("listitem").first()).toContainText("Fulana");

  // A escolha do item tira o jantar da lista e o põe no item escolhido.
  const aEscolher = page.getByRole("region", { name: "A escolher" });
  await aEscolher.getByRole("button", { name: `Conta em Viagem ${s}` }).click();
  await expect(aEscolher).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Itens do planejamento" }).getByRole("row").filter({ hasText: `Viagem ${s}` })).toContainText("R$ 200,00");

  // Sem internet, o mês já aberto mostra a última resposta.
  await context.setOffline(true);
  await page.getByRole("link", { name: "Mês anterior" }).click();
  await page.getByRole("link", { name: "Próximo mês" }).click();
  await expect(page.getByRole("heading", { name: `Março de ${ano}` })).toBeVisible();
  await expect(page.getByText(/Sem internet: atualizado às \d\d:\d\d/)).toBeVisible();
  await expect(fechamento).toContainText("R$ 800,00 de despesas");
  await context.setOffline(false);
});

test("o mês vazio copia o planejamento do anterior ou aplica o modelo padrão", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/configuracoes");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Configurações" })).toBeVisible();
  const api = await apiDaPagina(page);
  const { criar } = api;
  const ano = await anoVazio(api, (a) => [`${a}-04`, `${a}-05`, `${a}-06`]);
  const [casa] = [await criar("/api/categorias", { nome: `Casa ${s}`, tipo: "despesa" })];
  await criar("/api/categorias", { nome: `Lazer ${s}`, tipo: "despesa" });
  await criar(`/api/planejamento/${ano}-04/itens`, { id: randomUUID(), categoria_id: casa.id, valor_centavos: 150000 });

  // O modelo padrão se monta nas configurações.
  await page.reload();
  await page.getByRole("link", { name: "Modelo padrão do planejamento" }).click();
  await expect(page.getByRole("heading", { name: "Modelo padrão do planejamento" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Salvar modelo padrão" })).toBeEnabled();
  for (const item of await page.getByRole("button", { name: /^Tirar / }).all()) await item.click();
  await page.getByLabel("Adicionar item").selectOption({ label: `Lazer ${s}` });
  await page.getByRole("textbox", { name: `Lazer ${s}` }).fill("250,50");
  await page.getByRole("button", { name: "Salvar modelo padrão" }).click();
  await expect(page.getByRole("status")).toHaveText("Modelo padrão salvo.");

  await page.goto(`/#/mes/${ano}-05`);
  const itens = page.getByRole("region", { name: "Itens do planejamento" });
  await expect(itens).toContainText("Nenhum item planejado neste mês.");
  await itens.getByRole("button", { name: "Copiar do mês anterior" }).click();
  await expect(itens.getByRole("row").filter({ hasText: `Casa ${s}` })).toContainText("R$ 1.500,00");

  await page.getByRole("link", { name: "Próximo mês" }).click();
  await expect(page.getByRole("heading", { name: `Junho de ${ano}` })).toBeVisible();
  await itens.getByRole("button", { name: "Aplicar modelo padrão" }).click();
  await expect(itens.getByRole("row").filter({ hasText: `Lazer ${s}` })).toContainText("R$ 250,50");
});

test("o casal cria um item avulso, muda o valor e exclui, sem passar pelo modelo padrão", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/configuracoes");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Configurações" })).toBeVisible();
  const api = await apiDaPagina(page);
  const { criar } = api;
  const ano = await anoVazio(api, (a) => [`${a}-07`]);
  await criar("/api/categorias", { nome: `Casa ${s}`, tipo: "despesa" });

  await page.goto(`/#/mes/${ano}-07`);
  const itens = page.getByRole("region", { name: "Itens do planejamento" });
  await expect(itens).toContainText("Nenhum item planejado neste mês.");
  await itens.getByLabel("Categoria do novo item").selectOption({ label: `Casa ${s}` });
  await itens.getByLabel("Valor do novo item").fill("300,00");
  await itens.getByRole("button", { name: "Adicionar item" }).click();
  const linha = itens.getByRole("row").filter({ hasText: `Casa ${s}` });
  await expect(linha).toContainText("R$ 300,00");

  await linha.getByRole("button", { name: `Mudar valor de Casa ${s}` }).click();
  await itens.getByLabel(`Novo valor de Casa ${s}`).fill("450,50");
  await itens.getByRole("button", { name: "Salvar valor" }).click();
  await expect(linha).toContainText("R$ 450,50");

  await linha.getByRole("button", { name: `Excluir Casa ${s}` }).click();
  await expect(itens.getByRole("row").filter({ hasText: `Casa ${s}` })).toHaveCount(0);
  await expect(itens).toContainText("Nenhum item planejado neste mês.");
});

/** Um mês de um ano antigo e vazio, com a conta, duas categorias com item no planejamento e um jantar nas duas (o "A escolher"). */
async function prepararMesComJantar(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/mes");
  await entrar(page);
  await expect(page.getByText("mês atual")).toBeVisible();
  const api = await apiDaPagina(page);
  const ano = await anoVazio(api, (a) => [`${a}-03`]);
  const mes = `${ano}-03`;
  const conta = await api.criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const mercado = (await api.criar("/api/categorias", { nome: `Mercado ${s}`, tipo: "despesa" })).id as string;
  const viagem = (await api.criar("/api/categorias", { nome: `Viagem ${s}`, tipo: "despesa" })).id as string;
  for (const categoria of [mercado, viagem]) await api.criar(`/api/planejamento/${mes}/itens`, { id: randomUUID(), categoria_id: categoria, valor_centavos: 50000 });
  await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 20000,
    data: `${mes}-07`,
    descricao: `Jantar ${s}`,
    conta_id: conta.id,
    categoria_ids: [mercado, viagem],
    tags: [],
  });
  return { s, mes, api };
}

const abrirMes = (page: Page, mes: string) => page.evaluate((m) => (window.location.hash = `#/mes/${m}`), mes);

test("sem internet, o Mês mostra os lançamentos da última leitura e avisa", async ({ page, context }) => {
  const { s, mes } = await prepararMesComJantar(page);
  await abrirMes(page, mes);
  const aEscolher = page.getByRole("region", { name: "A escolher" });
  await expect(aEscolher).toContainText(`Jantar ${s}`);
  await expect(page.getByText("Sem internet: os lançamentos do mês são as da última leitura.")).toHaveCount(0);

  await context.setOffline(true);
  await abrirMes(page, "1000-01");
  await abrirMes(page, mes);
  await expect(page.getByText("Sem internet: os lançamentos do mês são as da última leitura.")).toBeVisible();
  await expect(aEscolher).toContainText(`Jantar ${s}`);
  const ranking = page.getByRole("region", { name: "Ranking" });
  await ranking.getByRole("button", { name: new RegExp(`Mercado ${s}`) }).click();
  await expect(page.getByRole("dialog", { name: `Mercado ${s}` })).toContainText(`Jantar ${s}`);
  await context.setOffline(false);
});

test("sem internet e sem resposta guardada dos lançamentos, o Mês diz que o A escolher e o Ranking precisam de internet", async ({ page }) => {
  const { s, mes } = await prepararMesComJantar(page);
  // A leitura do mês chega; a dos lançamentos do mês nunca veio ao aparelho.
  await page.route(`**/api/meses/${mes}/lancamentos`, (rota) => rota.abort("internetdisconnected"));
  await abrirMes(page, mes);
  await expect(page.getByRole("heading", { name: /Março de/ })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "precisam dos lançamentos do mês, que não estão no aparelho" })).toContainText('Sem internet: o "A escolher" e o Ranking precisam');
  await expect(page.getByRole("region", { name: "A escolher" })).toHaveCount(0);
  await expect(page.getByText(`Jantar ${s}`)).toHaveCount(0);
});

test("um lançamento não enviado aparece no A escolher e no Ranking do Mês sem internet", async ({ page, context }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/mes");
  await entrar(page);
  const api = await apiDaPagina(page);
  const hoje = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
  const mes = hoje.slice(0, 7);
  const conta = await api.criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const mercado = (await api.criar("/api/categorias", { nome: `Mercado ${s}`, tipo: "despesa" })).id as string;
  const viagem = (await api.criar("/api/categorias", { nome: `Viagem ${s}`, tipo: "despesa" })).id as string;
  for (const categoria of [mercado, viagem]) await api.criar(`/api/planejamento/${mes}/itens`, { id: randomUUID(), categoria_id: categoria, valor_centavos: 50000 });
  await api.criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos: 4500, data: hoje, descricao: `Jantar ${s}`, conta_id: conta.id, categoria_ids: [mercado, viagem], tags: [] });
  await page.reload();
  await expect(page.getByRole("region", { name: "A escolher" })).toContainText(`Jantar ${s}`);

  // Sem internet, a edição do valor fica na fila; a resposta guardada do mês é a de antes dela.
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Histórico" }).click();
  const linha = page.getByRole("listitem").filter({ hasText: `Jantar ${s}` });
  await expect(linha).toBeVisible();
  await context.setOffline(true);
  await linha.getByRole("link", { name: `Editar Jantar ${s}` }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 45,00");
  await page.getByRole("button", { name: "0", exact: true }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(linha).toContainText("⏳ não enviado");

  await abrirMes(page, mes);
  const aEscolher = page.getByRole("region", { name: "A escolher" });
  await expect(aEscolher).toContainText(`Jantar ${s}`);
  await expect(aEscolher).toContainText("R$ 450,00");
  const ranking = page.getByRole("region", { name: "Ranking" });
  await ranking.getByRole("button", { name: new RegExp(`Mercado ${s}`) }).click();
  await expect(page.getByRole("dialog", { name: `Mercado ${s}` })).toContainText("R$ 450,00");
  await context.setOffline(false);
});
