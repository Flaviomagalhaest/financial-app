import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { digitar } from "./lancar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

/** Dia `deslocamento` dias a partir de hoje em São Paulo, como `AAAA-MM-DD`. */
function dia(deslocamento: number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(Date.now() + deslocamento * 86_400_000));
}

/** `2026-11-01` vira `11/2026`. */
const mesDaFatura = (iso: string) => `${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** O valor de uma linha do resumo da fatura (`dt` e `dd` lado a lado). */
const resumo = (page: Page, nome: string) =>
  page.getByLabel("Resumo da fatura").locator("dt", { hasText: new RegExp(`^${nome}$`) }).locator("xpath=following-sibling::dd[1]");

/** Entra e prepara pela API um cartão, uma categoria e uma compra de R$ 100,00 hoje. */
async function prepararFatura(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [cartaoNome, categoriaNome, compraNome] = [`Visa ${s}`, `Vestuário ${s}`, `Tênis ${s}`];
  await page.goto("/#/historico");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  const api = await apiDaPagina(page);
  const cartao = await api.criar("/api/cartoes", { nome: cartaoNome, dia_fechamento: 10, dia_vencimento: 20 });
  const categoria = await api.criar("/api/categorias", { nome: categoriaNome, tipo: "despesa" });
  const compra = await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 10000,
    data: dia(0),
    descricao: compraNome,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
  });
  await page.goto(`/#/cartoes/${cartao.id}/${compra.mes}`);
  await expect(resumo(page, "Total")).toHaveText("R$ 100,00");
  return { s, api, cartao, categoria, compra, cartaoNome, categoriaNome };
}

test("lança um crédito na tela da fatura sem categoria: diminui a fatura, aparece como estorno avulso e se edita", async ({ page }) => {
  const { s, cartao, compra, cartaoNome } = await prepararFatura(page);
  const nome = `Centavos ${s}`;

  await page.getByRole("link", { name: "Lançar crédito" }).click();
  await expect(page.getByRole("heading", { name: "Lançar crédito", level: 2 })).toBeVisible();
  // Abre no cartão da fatura, sem tipo nem conta para escolher, e a categoria é opcional.
  await expect(page.getByRole("button", { name: cartaoNome })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: "Receita" })).toHaveCount(0);
  await expect(page.getByText(`Entra na fatura de ${mesDaFatura(compra.mes)}`)).toBeVisible();
  await expect(page.getByRole("button", { name: "Salvar" })).toBeDisabled();
  await digitar(page, "3", "7");
  await expect(page.getByTestId("valor")).toHaveText("R$ 0,37");
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(nome);
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();

  const credito = page.getByRole("listitem").filter({ hasText: nome });
  await expect(credito).toContainText("+ R$ 0,37");
  await expect(credito).toContainText("estorno avulso");
  // O total da fatura vem do servidor: espera a fila enviar antes de abri-la.
  await expect(credito).not.toContainText("não enviado");
  await page.goto(`/#/cartoes/${cartao.id}/${compra.mes}`);
  await expect(resumo(page, "Estornos")).toHaveText("− R$ 0,37");
  await expect(resumo(page, "Total")).toHaveText("R$ 99,63");
  await expect(page.getByRole("listitem").filter({ hasText: nome })).toContainText("+ R$ 0,37");

  // Editar o crédito: o valor muda, e ele não vira receita nem sai do cartão.
  await page.goto("/#/historico");
  await page.getByRole("link", { name: `Editar ${nome}` }).click();
  await expect(page.getByRole("heading", { name: "Editar crédito", level: 2 })).toBeVisible();
  await page.getByRole("button", { name: "Apagar" }).click();
  await digitar(page, "5");
  await expect(page.getByTestId("valor")).toHaveText("R$ 0,35");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: nome })).toContainText("+ R$ 0,35");
  await expect(page.getByRole("listitem").filter({ hasText: nome })).not.toContainText("não enviado");
  await page.goto(`/#/cartoes/${cartao.id}/${compra.mes}`);
  await expect(resumo(page, "Total")).toHaveText("R$ 99,65");
});

test("o crédito com categoria entra na fila sem internet e sobe quando a rede volta, e o Repetir último não o oferece", async ({ page, context }) => {
  const { s, api, cartao, compra, categoriaNome } = await prepararFatura(page);
  const nome = `Crédito ${s}`;

  await context.setOffline(true);
  await page.getByRole("link", { name: "Lançar crédito" }).click();
  await digitar(page, "2", "5", "0", "0");
  await page.getByRole("button", { name: categoriaNome }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(nome);
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  const credito = page.getByRole("listitem").filter({ hasText: nome });
  await expect(credito).toContainText("+ R$ 25,00");
  await expect(credito).toContainText(categoriaNome);
  await expect(credito).toContainText("⏳ não enviado");

  // O crédito não serve de modelo para o "Repetir último" do lançamento novo.
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await expect(page.getByRole("button", { name: /^Repetir último/ })).toHaveCount(0);
  await page.goto("/#/historico");

  await context.setOffline(false);
  await expect(credito).not.toContainText("não enviado");
  const gravados = (await api.ler("/api/lancamentos")) as { descricao: string; estorno_avulso: boolean; valor_centavos: number; categoria_ids: string[] }[];
  expect(gravados.find((l) => l.descricao === nome)).toMatchObject({ estorno_avulso: true, valor_centavos: 2500 });
  const fatura = (await api.ler(`/api/cartoes/${cartao.id}/faturas`)).find((f: { mes: string }) => f.mes === compra.mes);
  expect(fatura).toMatchObject({ total_centavos: 7500 });
});
