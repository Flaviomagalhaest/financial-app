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

const porExtenso = (iso: string) => iso.split("-").reverse().join("/");
/** `2026-11-01` vira `11/2026`. */
const mesDaFatura = (iso: string) => `${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** Entra e prepara pela API um cartão, uma categoria, uma tag e uma compra de R$ 100,00 `deslocamento` dias de hoje. */
async function prepararCompra(page: Page, deslocamento = 0) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [cartaoNome, categoriaNome, tag, compraNome] = [`Visa ${s}`, `Vestuário ${s}`, `troca ${s}`, `Tênis ${s}`];
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
    data: dia(deslocamento),
    descricao: compraNome,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
    tags: [tag],
  });
  await page.reload();
  return { s, api, cartao, categoria, compra, cartaoNome, categoriaNome, tag, compraNome };
}

test("estorna parte da compra no cartão: abre preenchido, mostra a fatura e liga o estorno à compra nas duas pontas", async ({ page }) => {
  const { compra, cartaoNome, categoriaNome, tag, compraNome } = await prepararCompra(page);

  const naCompra = page.getByRole("listitem").filter({ hasText: compraNome });
  await naCompra.getByRole("link", { name: `Estornar ${compraNome}` }).click();

  // Já vem com o valor, as categorias, as tags e o cartão da compra, e a data de hoje.
  await expect(page.getByRole("heading", { name: "Estornar compra", level: 2 })).toBeVisible();
  await expect(page.getByTestId("valor")).toHaveText("R$ 100,00");
  await expect(page.getByRole("button", { name: cartaoNome })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: categoriaNome })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: /^Detalhes/ })).toContainText(`#${tag}`);
  await expect(page.getByText(`Entra na fatura de ${mesDaFatura(compra.mes)}`)).toBeVisible();

  // O valor pode ser menor: R$ 40,00 de R$ 100,00.
  for (let i = 0; i < 5; i++) await page.getByRole("button", { name: "Apagar" }).click();
  await digitar(page, "4", "00", "0");
  await expect(page.getByTestId("valor")).toHaveText("R$ 40,00");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  // Nas duas pontas: a compra diz quando foi estornada e o estorno diz de qual compra é, como crédito.
  const estorno = page.getByRole("listitem").filter({ hasText: `estorno de ${compraNome}` });
  await expect(estorno).toContainText("+ R$ 40,00");
  await expect(estorno).toContainText(categoriaNome);
  await expect(estorno).toContainText(`#${tag}`);
  const original = page.getByRole("listitem").filter({ hasText: compraNome }).filter({ hasText: "estornada em" });
  await expect(original).toContainText(`estornada em ${porExtenso(dia(0))}`);
  await expect(original).toContainText("− R$ 100,00");
});

/** O valor de uma linha do resumo da fatura (`dt` e `dd` lado a lado). */
const resumo = (page: Page, nome: string) =>
  page.getByLabel("Resumo da fatura").locator("dt", { hasText: new RegExp(`^${nome}$`) }).locator("xpath=following-sibling::dd[1]");

test("a fatura mostra compras, estornos e ajuste, e o ajuste vale pelo valor real da fatura ou pela diferença, positivo ou negativo", async ({ page }) => {
  const { api, cartao, categoria, compra, tag, compraNome } = await prepararCompra(page);
  await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 3000,
    data: dia(0),
    descricao: `Estorno ${compraNome}`,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
    tags: [tag],
    estorno_de: compra.id,
  });

  await page.goto(`/#/cartoes/${cartao.id}/${compra.mes}`);
  await expect(page.getByRole("heading", { name: `Fatura de ${mesDaFatura(compra.mes)}`, level: 2 })).toBeVisible();
  await expect(resumo(page, "Compras")).toHaveText("R$ 100,00");
  await expect(resumo(page, "Estornos")).toHaveText("− R$ 30,00");
  await expect(resumo(page, "Ajuste")).toHaveText("R$ 0,00");
  await expect(resumo(page, "Total")).toHaveText("R$ 70,00");
  const estorno = page.getByRole("listitem").filter({ hasText: `estorno de ${compraNome}` });
  await expect(estorno).toContainText("+ R$ 30,00");

  // O banco cobra R$ 65,00: informa o valor real e o app calcula o ajuste (−R$ 5,00).
  await page.getByRole("button", { name: "Ajustar fatura" }).click();
  const formulario = page.getByRole("form", { name: "Ajustar fatura" });
  await formulario.getByRole("radio", { name: "Valor real da fatura" }).check();
  await formulario.getByLabel("Valor", { exact: true }).fill("65,00");
  await expect(formulario).toContainText("Ajuste de − R$ 5,00");
  await formulario.getByRole("button", { name: "Salvar ajuste" }).click();
  await expect(resumo(page, "Ajuste")).toHaveText("− R$ 5,00");
  await expect(resumo(page, "Total")).toHaveText("R$ 65,00");
  expect((await api.ler(`/api/cartoes/${cartao.id}/faturas`)).find((f: { mes: string }) => f.mes === compra.mes)).toMatchObject({ ajuste_centavos: -500, total_centavos: 6500 });

  // Depois o banco cobra R$ 10,00 a mais do que o app mostra: a diferença soma ao ajuste que já existe.
  await page.getByRole("button", { name: "Ajustar fatura" }).click();
  await formulario.getByRole("radio", { name: "Diferença" }).check();
  await formulario.getByLabel("Valor", { exact: true }).fill("10,00");
  await expect(formulario).toContainText("Ajuste de + R$ 5,00");
  await formulario.getByRole("button", { name: "Salvar ajuste" }).click();
  await expect(resumo(page, "Ajuste")).toHaveText("+ R$ 5,00");
  await expect(resumo(page, "Total")).toHaveText("R$ 75,00");
});

test("cancelar a compra de uma fatura aberta é excluir; depois do fechamento a tela sugere o estorno", async ({ page }) => {
  // 35 dias atrás cai numa fatura já fechada (cartão que fecha dia 10); hoje, na aberta.
  const { api, cartao, categoria, compra: antiga, compraNome: nomeAntiga } = await prepararCompra(page, -35);
  const nomeDeHoje = `Padaria ${nomeAntiga}`;
  const deHoje = await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 2500,
    data: dia(0),
    descricao: nomeDeHoje,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
  });
  await page.reload();

  // Aberta: a exclusão que já existia, com a confirmação, e a compra some de tudo.
  const linhaDeHoje = page.getByRole("listitem").filter({ hasText: nomeDeHoje });
  page.once("dialog", (dialogo) => void dialogo.accept());
  await linhaDeHoje.getByRole("button", { name: `Excluir ${nomeDeHoje}` }).click();
  await expect(linhaDeHoje).toHaveCount(0);
  // A linha some assim que a exclusão entra na fila; a fatura só muda quando ela sobe ao servidor.
  await expect
    .poll(async () => (await api.ler(`/api/cartoes/${cartao.id}/faturas`)).find((f: { mes: string }) => f.mes === deHoje.mes)?.total_centavos ?? 0)
    .toBe(0);

  // Fechada: não exclui; sugere o estorno, que abre a compra para estornar.
  const linhaAntiga = page.getByRole("listitem").filter({ hasText: nomeAntiga });
  let perguntou = false;
  page.on("dialog", (dialogo) => {
    perguntou = true;
    void dialogo.dismiss();
  });
  await linhaAntiga.getByRole("button", { name: `Excluir ${nomeAntiga}` }).click();
  const sugestao = linhaAntiga.getByRole("group", { name: "Fatura fechada" });
  await expect(sugestao).toContainText(`A fatura de ${mesDaFatura(antiga.mes)} já fechou`);
  expect(perguntou).toBe(false);
  await expect(linhaAntiga).toHaveCount(1);
  await sugestao.getByRole("link", { name: "Estornar" }).click();
  await expect(page.getByRole("heading", { name: "Estornar compra", level: 2 })).toBeVisible();
  await expect(page.getByTestId("valor")).toHaveText("R$ 100,00");

  // Na própria fatura fechada, o aviso também manda estornar.
  await page.goto(`/#/cartoes/${cartao.id}/${antiga.mes}`);
  await expect(page.getByText("Esta fatura já fechou: para cancelar uma compra, estorne-a.")).toBeVisible();
});

test("sem internet o estorno entra na fila e sobe quando a rede volta, mas o ajuste da fatura exige internet", async ({ page, context }) => {
  const { api, cartao, compra, compraNome } = await prepararCompra(page);
  // Deixa a fatura e a lista guardadas no aparelho.
  await page.goto(`/#/cartoes/${cartao.id}/${compra.mes}`);
  await expect(resumo(page, "Total")).toHaveText("R$ 100,00");

  await context.setOffline(true);
  await expect(page.getByRole("button", { name: "Ajustar fatura" })).toBeDisabled();
  await expect(page.getByText("Ajustar a fatura precisa de internet.")).toBeVisible();

  await page.getByRole("link", { name: `Estornar ${compraNome}` }).click();
  await expect(page.getByRole("heading", { name: "Estornar compra", level: 2 })).toBeVisible();
  await expect(page.getByText(`Entra na fatura de ${mesDaFatura(compra.mes)}`)).toBeVisible();
  await page.getByRole("button", { name: "Salvar" }).click();
  const estorno = page.getByRole("listitem").filter({ hasText: `estorno de ${compraNome}` });
  await expect(estorno).toContainText("+ R$ 100,00");
  await expect(estorno).toContainText("⏳ não enviado");
  // Toda a compra foi devolvida: não há mais o que estornar.
  await expect(page.getByRole("listitem").filter({ hasText: compraNome }).filter({ hasText: "estornada em" })).not.toContainText("Estornar");

  await context.setOffline(false);
  await expect(estorno).not.toContainText("não enviado");
  const gravados = (await api.ler("/api/lancamentos")) as { estorno_de: string | null; valor_centavos: number }[];
  expect(gravados.find((l) => l.estorno_de === compra.id)).toMatchObject({ valor_centavos: 10000 });
});

test("um segundo estorno começa no que ainda resta da compra e não deixa passar dele; o estorno editado mantém as categorias", async ({ page }) => {
  const { api, cartao, categoria, categoriaNome, compra, tag, compraNome } = await prepararCompra(page);
  await api.criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 4000,
    data: dia(0),
    descricao: `Estorno ${compraNome}`,
    conta_id: cartao.id,
    categoria_ids: [categoria.id],
    tags: [tag],
    estorno_de: compra.id,
  });
  await page.reload();

  await page.getByRole("listitem").filter({ hasText: compraNome }).filter({ hasText: "estornada em" }).getByRole("link", { name: `Estornar ${compraNome}` }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 60,00");
  await expect(page.getByText("ainda dá para estornar até R$ 60,00")).toBeVisible();
  await page.getByRole("button", { name: "0", exact: true }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 600,00");
  await expect(page.getByRole("button", { name: "Salvar" })).toBeDisabled();

  // As categorias e as tags do estorno são as da compra e não mudam.
  await page.goto("/#/historico");
  await page.getByRole("link", { name: `Editar Estorno ${compraNome}` }).click();
  await expect(page.getByRole("heading", { name: "Editar estorno", level: 2 })).toBeVisible();
  await expect(page.getByTestId("valor")).toHaveText("R$ 40,00");
  await expect(page.getByRole("button", { name: categoriaNome })).toBeDisabled();
  // Só as categorias da compra aparecem.
  await expect(page.getByRole("button", { name: /^Vestuário/ })).toHaveCount(1);
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await expect(page.getByRole("button", { name: `#${tag}`, exact: true })).toBeDisabled();
});
