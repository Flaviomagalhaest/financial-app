import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";

test.use({ timezoneId: "America/Sao_Paulo" });

/** Ainda não há tela de itens avulsos do planejamento: o teste prepara o mês pela API, com o token da página. */
async function tokenDaPagina(page: Page): Promise<string> {
  const pedido = page.waitForRequest((r) => r.url().includes("/api/") && !!r.headers().authorization);
  await page.reload();
  return (await pedido).headers().authorization;
}

test("a aba Mês navega até um mês passado, lê o fechamento, compara, abre o ranking e escolhe o item", async ({ page, context }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  // Os testes dividem o banco: um ano antigo sorteado deixa os totais do mês só com o que este teste lança.
  const ano = 1100 + Math.floor(Math.random() * 800);
  const [marco, fevereiro, marcoDoAnoPassado] = [`${ano}-03`, `${ano}-02`, `${ano - 1}-03`];
  await page.goto("/#/mes");
  await entrar(page);
  await expect(page.getByText("mês atual")).toBeVisible();
  await expect(page.getByRole("region", { name: "Despesas × planejamento" })).toBeVisible();

  const headers = { authorization: await tokenDaPagina(page) };
  const criar = async (caminho: string, data: object) => {
    const resposta = await page.request.post(caminho, { headers, data });
    expect(resposta.ok(), await resposta.text()).toBe(true);
    return resposta.json();
  };
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
  await lancar(50000, `${fevereiro}-06`, [mercado]);
  await lancar(100000, `${marcoDoAnoPassado}-06`, [mercado]);

  await page.goto(`/#/mes/${fevereiro}`);
  await page.getByRole("link", { name: "Próximo mês" }).click();
  await expect(page.getByRole("heading", { name: `Março de ${ano}` })).toBeVisible();
  const fechamento = page.getByRole("region", { name: "Fechamento do mês" });
  await expect(fechamento).toContainText(`Março de ${ano} fechou com R$ 4.000,00 de receitas e R$ 800,00 de despesas. Sobraram R$ 3.200,00 (80% das receitas).`);
  await expect(fechamento).toContainText(`Passou do planejado em Mercado ${s} (+R$ 100,00); 2 de 3 itens ficaram dentro.`);
  await expect(fechamento).toContainText(`Em relação a fevereiro de ${ano}, as despesas subiram 60%. Em relação a março de ${ano - 1}, as despesas caíram 20%.`);

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
  const ano = 1100 + Math.floor(Math.random() * 800);
  await page.goto("/#/configuracoes");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Configurações" })).toBeVisible();
  const headers = { authorization: await tokenDaPagina(page) };
  const criar = async (caminho: string, data: object) => {
    const resposta = await page.request.post(caminho, { headers, data });
    expect(resposta.ok(), await resposta.text()).toBe(true);
    return resposta.json();
  };
  const [casa] = [await criar("/api/categorias", { nome: `Casa ${s}`, tipo: "despesa" })];
  await criar("/api/categorias", { nome: `Lazer ${s}`, tipo: "despesa" });
  await criar(`/api/planejamento/${ano}-04/itens`, { id: randomUUID(), categoria_id: casa.id, valor_centavos: 150000 });

  // O modelo padrão se monta nas configurações.
  await page.reload();
  await page.getByRole("link", { name: "Modelo padrão do planejamento" }).click();
  await expect(page.getByRole("heading", { name: "Modelo padrão do planejamento" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Salvar modelo" })).toBeEnabled();
  for (const item of await page.getByRole("button", { name: /^Tirar / }).all()) await item.click();
  await page.getByLabel("Adicionar item").selectOption({ label: `Lazer ${s}` });
  await page.getByRole("textbox", { name: `Lazer ${s}` }).fill("250,50");
  await page.getByRole("button", { name: "Salvar modelo" }).click();
  await expect(page.getByRole("status")).toHaveText("Modelo salvo.");

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
