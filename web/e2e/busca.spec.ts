import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { lancar } from "./lancar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

/** Dia `deslocamento` dias a partir de hoje em São Paulo, como `AAAA-MM-DD`. */
function dia(deslocamento: number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(Date.now() + deslocamento * 86_400_000));
}

/** `2026-11-01` vira `11/2026`. */
const mesDaFatura = (iso: string) => `${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

type Api = Awaited<ReturnType<typeof apiDaPagina>>;

/** Uma conta, um cartão e duas categorias com o sufixo `s`, que a busca pelo texto isola dos outros testes. */
async function prepararCadastro(api: Api, s: string) {
  const conta = await api.criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const poupanca = await api.criar("/api/contas", { nome: `Poupança ${s}`, tipo: "poupanca" });
  const cartao = await api.criar("/api/cartoes", { nome: `Visa ${s}`, dia_fechamento: 10, dia_vencimento: 20 });
  const mercado = await api.criar("/api/categorias", { nome: `Mercado ${s}`, tipo: "despesa" });
  const eletro = await api.criar("/api/categorias", { nome: `Eletro ${s}`, tipo: "despesa" });
  const salario = await api.criar("/api/categorias", { nome: `Salário ${s}`, tipo: "receita" });
  const lancamento = (corpo: object) =>
    api.criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", descricao: "", conta_id: conta.id, categoria_ids: [mercado.id], tags: [], ...corpo });
  return { conta, poupanca, cartao, mercado, eletro, salario, lancamento };
}

const buscarPeloTexto = async (page: Page, texto: string) => {
  await page.getByLabel("Buscar na descrição").fill(texto);
  await expect(page).toHaveURL(new RegExp(`texto=${encodeURIComponent(texto).replace(/%20/g, "\\+")}`));
};

test("a lupa abre a busca, combina texto e filtros, mostra o parcelamento numa linha e os totais", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/mes");
  await entrar(page);
  const api = await apiDaPagina(page);
  const { conta, poupanca, cartao, mercado, eletro, salario, lancamento } = await prepararCadastro(api, s);
  await lancamento({ valor_centavos: 10000, data: dia(-3), descricao: `Feira ${s}`, tags: [`casa ${s}`] });
  await lancamento({ valor_centavos: 100000, data: dia(-2), descricao: `Salário ${s}`, tipo: "receita", categoria_ids: [salario.id] });
  await lancamento({ valor_centavos: 30000, data: dia(20), descricao: `Aluguel ${s}` });
  // O parcelamento antigo já tem todas as parcelas realizadas.
  await api.criar("/api/parcelamentos", { id: randomUUID(), valor_total_centavos: 250000, parcelas: 10, descricao: `Geladeira ${s}`, conta_id: cartao.id, categoria_ids: [eletro.id], data: "2020-03-04" });
  await api.criar("/api/transferencias", { id: randomUUID(), conta_origem_id: conta.id, conta_destino_id: poupanca.id, valor_centavos: 5000, data: dia(-1), descricao: `Reserva ${s}` });

  await page.getByRole("link", { name: "Buscar lançamentos" }).click();
  await expect(page.getByRole("heading", { name: "Busca", level: 2 })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Histórico" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByText("Período pela data da compra; a aba Mês conta pelo mês da fatura.")).toBeVisible();

  await buscarPeloTexto(page, s);
  const resultado = page.getByRole("list", { name: "Resultado da busca" });
  const linhas = resultado.locator(":scope > li");
  await expect(linhas).toHaveCount(5);
  const totais = page.getByRole("definition");
  // A transferência aparece na lista, mas fica fora dos totais e da contagem.
  await expect(page.getByLabel("Totais da busca")).toContainText("Lançamentos4");
  await expect(totais.nth(1)).toHaveText("R$ 2.600,00");
  await expect(totais.nth(2)).toHaveText("R$ 1.000,00");
  await expect(totais.nth(3)).toHaveText("-R$ 1.600,00");
  await expect(page.getByLabel("Previstos à parte")).toContainText("R$ 300,00 de despesas e R$ 0,00 de receitas, saldo de -R$ 300,00");
  // Mais recente primeiro: o aluguel previsto, a reserva, o salário, a feira e a geladeira de 2020.
  await expect(linhas.nth(0)).toContainText(`Aluguel ${s}`);
  await expect(linhas.nth(1)).toContainText(`Reserva ${s}`);
  await expect(linhas.nth(1)).toContainText(`Corrente ${s} → Poupança ${s}`);
  await expect(linhas.nth(4)).toContainText("04/03/2020");
  await expect(linhas.nth(4)).toContainText("− R$ 2.500,00");

  // O parcelamento abre as parcelas, cada uma com a fatura e a situação.
  await linhas.nth(4).getByRole("button", { name: `Geladeira ${s} · 10x` }).click();
  const parcelas = page.getByRole("list", { name: `Parcelas de Geladeira ${s}` }).getByRole("listitem");
  await expect(parcelas).toHaveCount(10);
  await expect(parcelas.nth(2)).toContainText("03/10");
  await expect(parcelas.nth(2)).toContainText("− R$ 250,00");
  await expect(parcelas.nth(2)).toContainText("fatura de 05/2020 · realizado");

  // Maior valor primeiro.
  await page.getByRole("group", { name: "Ordem" }).getByRole("button", { name: "Maior valor" }).click();
  await expect(linhas.nth(0)).toContainText(`Geladeira ${s}`);

  // Filtros combinados: categoria E tag; a ficha escolhida tira o filtro.
  await page.getByRole("button", { name: /^Filtros/ }).click();
  const folha = page.getByRole("dialog", { name: "Filtros" });
  await folha.getByRole("group", { name: "Categorias" }).getByRole("button", { name: `Mercado ${s}` }).click();
  await folha.getByRole("button", { name: "Pronto" }).click();
  await expect(linhas).toHaveCount(2);
  await expect(page.getByLabel("Totais da busca")).toContainText("Lançamentos2");
  await page.getByRole("button", { name: `Tirar o filtro Mercado ${s}` }).click();
  await expect(linhas).toHaveCount(5);

  // O endereço guarda a busca: recarregar mostra o mesmo resultado.
  await page.reload();
  await expect(page.getByLabel("Buscar na descrição")).toHaveValue(s);
  await expect(linhas).toHaveCount(5);
  await expect(linhas.nth(0)).toContainText(`Geladeira ${s}`);
});

test("os atalhos do Mês e da fatura abrem a busca pelo mês da fatura, com os números da tela de origem", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/cartoes");
  await entrar(page);
  const api = await apiDaPagina(page);
  const { cartao, lancamento } = await prepararCadastro(api, s);
  const compra = await lancamento({ valor_centavos: 4200, data: dia(0), descricao: `Padaria ${s}`, conta_id: cartao.id });
  // Na conta, o mês em que conta é o da data: a feira cai no mesmo mês da fatura da padaria.
  await lancamento({ valor_centavos: 1800, data: compra.mes, descricao: `Feira ${s}` });

  // Da fatura, com a categoria escolhida lá.
  await page.goto(`/#/cartoes/${cartao.id}/${compra.mes}`);
  await page.getByLabel("Categoria").selectOption({ label: `Mercado ${s}` });
  await page.getByRole("link", { name: "Ver os lançamentos" }).click();
  await expect(page.getByRole("heading", { name: "Busca", level: 2 })).toBeVisible();
  await expect(page.getByRole("button", { name: `Tirar o filtro Fatura ${mesDaFatura(compra.mes)} · Visa ${s}` })).toBeVisible();
  await expect(page.getByRole("button", { name: `Tirar o filtro Mercado ${s}` })).toBeVisible();
  // Com o filtro Fatura, os números batem com a aba Mês: a linha fixa some.
  await expect(page.getByText("Período pela data da compra; a aba Mês conta pelo mês da fatura.")).toHaveCount(0);
  const linhas = page.getByRole("list", { name: "Resultado da busca" }).locator(":scope > li");
  await expect(linhas).toHaveCount(1);
  await expect(linhas.first()).toContainText(`Padaria ${s}`);
  await expect(linhas.first()).toContainText(`fatura de ${mesDaFatura(compra.mes)}`);

  // Do ranking do Mês: as despesas da categoria no mês em que contam.
  await page.goto(`/#/mes/${compra.mes.slice(0, 7)}`);
  const ranking = page.getByRole("region", { name: "Ranking" });
  await ranking.getByRole("button", { name: new RegExp(`Mercado ${s}`) }).click();
  const folha = page.getByRole("dialog", { name: `Mercado ${s}` });
  await expect(folha).toContainText("R$ 60,00");
  await folha.getByRole("link", { name: "Ver os lançamentos" }).click();
  await expect(page.getByRole("button", { name: `Tirar o filtro Conta em ${mesDaFatura(compra.mes)}` })).toBeVisible();
  await expect(page.getByRole("button", { name: "Tirar o filtro Despesa" })).toBeVisible();
  await expect(linhas).toHaveCount(2);
  const realizado = compra.mes <= dia(0);
  await expect(page.getByLabel("Totais da busca")).toContainText(realizado ? "R$ 60,00" : "R$ 42,00");
  if (!realizado) await expect(page.getByLabel("Previstos à parte")).toContainText("R$ 18,00 de despesas");
});

test("sem internet, a busca mostra o que o aparelho guarda, com os não enviados, e avisa que é parcial", async ({ page, context }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/historico");
  await entrar(page);
  const api = await apiDaPagina(page);
  const { lancamento } = await prepararCadastro(api, s);
  await lancamento({ valor_centavos: 10000, data: dia(-1), descricao: `Feira ${s}` });
  // Abrir a busca com internet guarda a lista dos lançamentos e o cadastro no aparelho.
  await page.goto(`/#/busca?texto=${s}`);
  const linhas = page.getByRole("list", { name: "Resultado da busca" }).locator(":scope > li");
  await expect(linhas).toHaveCount(1);
  await expect(linhas.first()).toContainText(`Corrente ${s}`);

  await context.setOffline(true);
  await lancar(page, { teclas: ["7", "00"], conta: `Corrente ${s}`, categoria: `Mercado ${s}`, descricao: `Padaria ${s}` });
  await page.getByRole("link", { name: "Buscar lançamentos" }).click();
  await buscarPeloTexto(page, s);
  await expect(page.getByRole("status")).toHaveText("Resultado parcial, sem internet: só o que este aparelho guarda.");
  await expect(linhas).toHaveCount(2);
  await expect(linhas.filter({ hasText: `Padaria ${s}` })).toContainText("⏳ não enviado");
  await expect(page.getByLabel("Totais da busca")).toContainText("R$ 107,00");

  await context.setOffline(false);
  await expect(page.getByRole("status")).toHaveCount(0);
  await expect(linhas).toHaveCount(2);
  await expect(linhas.filter({ hasText: `Padaria ${s}` })).not.toContainText("não enviado");
});
