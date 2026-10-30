import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import { tokenDaPagina } from "./api";
import { entrar } from "./entrar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

/** Dia `deslocamento` dias a partir de hoje em São Paulo, como `AAAA-MM-DD`. */
function dia(deslocamento: number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(Date.now() + deslocamento * 86_400_000));
}

const porExtenso = (iso: string) => iso.split("-").reverse().join("/");
/** `2026-11-01` vira `11/2026`. */
const mesDaFatura = (iso: string) => `${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

test("a aba Cartões mostra a fatura anterior, a atual e a próxima, e o detalhe agrupa as compras por dia com filtros", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [visa, mercado, viagem, adicional] = [`Visa ${s}`, `Mercado ${s}`, `Viagem ${s}`, `Visa da esposa ${s}`];
  await page.goto("/#/cartoes");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Cartões", level: 2 })).toBeVisible();
  const headers = { authorization: await tokenDaPagina(page) };
  const criar = async (caminho: string, data: object) => {
    const resposta = await page.request.post(caminho, { headers, data });
    expect(resposta.ok(), await resposta.text()).toBe(true);
    return resposta.json();
  };
  const cartao = await criar("/api/cartoes", { nome: visa, dia_fechamento: 10, dia_vencimento: 20 });
  const filho = await criar("/api/cartoes", { nome: adicional, titular_id: cartao.id });
  const catMercado = await criar("/api/categorias", { nome: mercado, tipo: "despesa" });
  const catViagem = await criar("/api/categorias", { nome: viagem, tipo: "despesa" });
  const comprar = (conta: string, categoria: { id: string }, centavos: number, data: string, descricao: string, tags: string[] = []) =>
    criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos: centavos, data, descricao, conta_id: conta, categoria_ids: [categoria.id], tags });

  // 35 dias atrás cai numa fatura já fechada; hoje, na aberta; daqui a 35 dias, na seguinte.
  const antiga = await comprar(cartao.id, catMercado, 10000, dia(-35), `Compra antiga ${s}`);
  const deHoje = await comprar(cartao.id, catMercado, 2500, dia(0), `Padaria ${s}`, [`café ${s}`]);
  await comprar(filho.id, catViagem, 40000, dia(0), `Hotel ${s}`);
  const futura = await comprar(cartao.id, catMercado, 7000, dia(35), `Compra futura ${s}`);

  await page.reload();
  const secao = page.getByRole("region", { name: visa });
  const anterior = secao.getByRole("listitem").filter({ hasText: "Anterior" });
  const atual = secao.getByRole("listitem").filter({ hasText: "Atual" });
  const proxima = secao.getByRole("listitem").filter({ hasText: "Próxima" });
  await expect(anterior).toContainText(`fatura de ${mesDaFatura(antiga.mes)}`);
  await expect(anterior).toContainText("Fechada");
  await expect(anterior).toContainText("R$ 100,00");
  // A fatura do titular soma a compra do adicional.
  await expect(atual).toContainText(`fatura de ${mesDaFatura(deHoje.mes)}`);
  await expect(atual).toContainText("Aberta");
  await expect(atual).toContainText("R$ 425,00");
  await expect(proxima).toContainText(`fatura de ${mesDaFatura(futura.mes)}`);
  await expect(proxima).toContainText("R$ 70,00");
  // O adicional não tem linha própria.
  await expect(page.getByRole("region", { name: adicional })).toHaveCount(0);

  await atual.getByRole("link", { name: /Abrir/ }).click();
  await expect(page.getByRole("heading", { name: `Fatura de ${mesDaFatura(deHoje.mes)}`, level: 2 })).toBeVisible();
  const grupo = page.getByRole("group", { name: porExtenso(dia(0)) });
  await expect(grupo.getByRole("listitem")).toHaveCount(2);
  await expect(grupo).toContainText(`Padaria ${s}`);
  await expect(grupo).toContainText(`Hotel ${s}`);
  await expect(grupo).toContainText(adicional);
  await expect(page.getByRole("link", { name: "Ver os lançamentos" })).toBeVisible();

  await page.getByLabel("Categoria").selectOption({ label: viagem });
  await expect(grupo.getByRole("listitem")).toHaveCount(1);
  await expect(grupo).toContainText(`Hotel ${s}`);
  await page.getByLabel("Categoria").selectOption({ label: "Todas" });
  await page.getByLabel("Tag").selectOption({ label: `#café ${s}` });
  await expect(grupo.getByRole("listitem")).toHaveCount(1);
  await expect(grupo).toContainText(`Padaria ${s}`);

  await page.getByRole("link", { name: "Voltar aos cartões" }).click();
  await expect(secao).toBeVisible();
});
