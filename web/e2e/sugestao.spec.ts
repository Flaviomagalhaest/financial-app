import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { cadastrar, digitar, lancar } from "./lancar";

/** Abre o novo lançamento pelo app, digita o valor e escreve a descrição na folha de detalhes. */
async function descrever(page: Page, teclas: string[], descricao: string) {
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, ...teclas);
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(descricao);
  return page.getByRole("list", { name: "Sugestões" }).getByRole("button");
}

test("sugere pelo histórico sem internet: escolher preenche os campos e mantém o valor, e a sugestão corrigida vem primeiro", async ({ page, context }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [conta, outraConta, mercado, casa] = [`Corrente ${s}`, `Carteira ${s}`, `Mercado ${s}`, `Casa ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova conta", outraConta, "carteira");
  await cadastrar(page, "Nova categoria", mercado, "despesa");
  await cadastrar(page, "Nova categoria", casa, "despesa");
  await lancar(page, { teclas: ["3", "00"], conta: outraConta, categoria: mercado, descricao: `Sacolão São ${s} (1/3)`, pessoa: "Flávio" });
  const sacolao = page.getByRole("listitem").filter({ hasText: `Sacolão São ${s}` });
  await expect(sacolao).not.toContainText("não enviado");
  // Ao abrir o app, o índice de sugestão vem do servidor e fica guardado no aparelho.
  const indice = page.waitForResponse((r) => r.url().endsWith("/api/sugestoes") && r.ok());
  await page.reload();
  await indice;

  await context.setOffline(true);
  // Uma letra ainda não sugere; sem acento, em maiúsculas e sem a parcela, a descrição é a mesma.
  const sugestoes = await descrever(page, ["4", "5", "00"], "s");
  await expect(sugestoes).toHaveCount(0);
  await page.getByLabel("Descrição").fill(`SACOLAO SAO ${s}`);
  await expect(sugestoes).toHaveCount(1);
  await expect(sugestoes.first()).toContainText(`${mercado} · ${outraConta} · Flávio`);
  // A palavra do meio que começa com o que se digitou também casa.
  await page.getByLabel("Descrição").fill(`${s}`);
  await expect(sugestoes).toHaveCount(1);

  await sugestoes.first().click();
  await expect(sugestoes).toHaveCount(0);
  await page.getByRole("button", { name: "Pronto" }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 45,00");
  await expect(page.getByRole("button", { name: outraConta })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: mercado })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: /^Detalhes/ })).toContainText("Flávio");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("listitem").filter({ hasText: "R$ 45,00" }).filter({ hasText: s })).toContainText("⏳ não enviado");

  // Corrigir as categorias do lançamento, mesmo sem internet, põe essa sugestão primeiro.
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Histórico" }).click();
  await sacolao.getByRole("link", { name: `Editar Sacolão São ${s} (1/3)` }).click();
  await page.getByRole("button", { name: mercado }).click();
  await page.getByRole("button", { name: casa }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(sacolao).toContainText("⏳ não enviado");
  await descrever(page, ["1", "00"], `sacolão são ${s}`);
  await expect(sugestoes.first()).toContainText(`${casa} · ${outraConta} · Flávio`);

  // Com a rede de volta, a fila sobe e o índice novo já não tem a sugestão corrigida.
  await context.setOffline(false);
  await expect(sugestoes).toHaveCount(1);
  await expect(sugestoes.first()).toContainText(`${casa} · ${outraConta} · Flávio`);
});

test("a sugestão de uma compra com partes oferece o pacote: escolher divide o valor da tela na proporção", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/historico");
  await entrar(page);
  const api = await apiDaPagina(page);
  const conta = await api.criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const roupa = await api.criar("/api/categorias", { nome: `Roupa ${s}`, tipo: "despesa" });
  const casa = await api.criar("/api/categorias", { nome: `Casa ${s}`, tipo: "despesa" });
  await api.criar("/api/lancamentos", {
    id: crypto.randomUUID(),
    tipo: "despesa",
    valor_centavos: 100000,
    data: new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date()),
    descricao: `Atacado ${s}`,
    conta_id: conta.id,
    categoria_ids: [],
    partes: [
      { id: crypto.randomUUID(), descricao: "Vestido", valor_centavos: 75000, categoria_ids: [roupa.id] },
      { id: crypto.randomUUID(), descricao: "Cortina", valor_centavos: 25000, categoria_ids: [casa.id] },
    ],
  });
  const indice = page.waitForResponse((r) => r.url().endsWith("/api/sugestoes") && r.ok());
  await page.reload();
  await indice;

  const sugestoes = await descrever(page, ["2", "00", "00"], `atacado ${s}`);
  await expect(sugestoes).toHaveCount(1);
  await expect(sugestoes.first()).toContainText("Vestido R$ 750,00 + Cortina R$ 250,00");
  await sugestoes.first().click();
  await page.getByRole("button", { name: "Pronto" }).click();

  const parte = (n: number) => page.getByRole("group", { name: `Parte ${n}`, exact: true });
  await expect(page.getByTestId("valor")).toHaveText("R$ 200,00");
  await expect(parte(1).getByLabel("Valor da parte")).toHaveValue("150,00");
  await expect(parte(2).getByLabel("Valor de Cortina")).toContainText("R$ 50,00");
  await expect(parte(1).getByRole("button", { name: `Roupa ${s}` })).toHaveAttribute("aria-pressed", "true");
});
