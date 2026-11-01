import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import { tokenDaPagina } from "./api";
import { entrar } from "./entrar";

test.use({ timezoneId: "America/Sao_Paulo" });

function dia(deslocamento: number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(Date.now() + deslocamento * 86_400_000));
}

const mesDaFatura = (iso: string) => `${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

test("o pagamento em parte deixa a fatura paga, a sobra vai para a seguinte e a correção a refaz", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const visa = `Visa ${s}`;
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
  const conta = await criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const categoria = await criar("/api/categorias", { nome: `Mercado ${s}`, tipo: "despesa" });
  const comprar = (centavos: number, data: string) =>
    criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos: centavos, data, descricao: `Compra ${s}`, conta_id: cartao.id, categoria_ids: [categoria.id], tags: [] });
  const antiga = await comprar(100000, dia(-35));
  await comprar(50000, dia(0));
  // Pagou 600,00 dos 1.000,00 da fatura fechada.
  await criar("/api/transferencias", { id: randomUUID(), conta_origem_id: conta.id, conta_destino_id: cartao.id, valor_centavos: 60000, data: dia(0), descricao: "Fatura", fatura_mes: antiga.mes });

  await page.reload();
  const secao = page.getByRole("region", { name: visa });
  const paga = secao.getByRole("listitem").filter({ hasText: `fatura de ${mesDaFatura(antiga.mes)}` });
  await expect(paga).toContainText("Paga");
  await expect(paga).toContainText("R$ 400,00 passou para a seguinte");
  await expect(secao.getByRole("listitem").filter({ hasText: "Atual" })).toContainText("R$ 400,00 de saldo anterior");

  // Paga em parte, ela não fica vencida na Hoje.
  await page.goto("/#/hoje");
  await expect(page.getByRole("heading", { name: "Hoje", level: 2 })).toBeVisible();
  await expect(page.getByRole("link", { name: `Abrir fatura de ${visa}` })).toHaveCount(0);

  await page.goto(`/#/cartoes/${cartao.id}/${antiga.mes}`);
  const resumo = page.getByLabel("Resumo da fatura");
  await expect(resumo).toContainText("Paga");
  await expect(resumo).toContainText("R$ 400,00");
  await page.getByRole("button", { name: "Corrigir fatura" }).click();
  const correcao = page.getByRole("form", { name: "Corrigir fatura" });
  await correcao.getByRole("group", { name: "Pagamento 1" }).getByLabel("Valor").fill("700,00");
  await expect(correcao).toContainText("Pago R$ 700,00 de R$ 1.000,00");
  await correcao.getByRole("button", { name: "Salvar correção" }).click();
  await expect(correcao).toHaveCount(0);
  await expect(resumo).toContainText("R$ 300,00");
  await expect(page.getByText("Esta fatura está paga")).toBeVisible();

  // Mudar o valor de uma compra da fatura paga seria recusado: a tela de lançar avisa e leva à correção.
  await page.goto(`/#/novo/${antiga.id}`);
  await expect(page.getByTestId("valor")).toHaveText("R$ 1.000,00");
  await page.getByRole("button", { name: "0", exact: true }).click();
  const alerta = page.getByRole("alert").filter({ hasText: `A fatura de ${mesDaFatura(antiga.mes)} está paga` });
  await expect(alerta).toBeVisible();
  await alerta.getByRole("link", { name: "Corrigir a fatura" }).click();
  await expect(page.getByRole("button", { name: "Corrigir fatura" })).toBeVisible();
});

test("a correção do valor de uma compra com partes acerta a última parte", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const visa = `Visa ${s}`;
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
  const conta = await criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const roupa = await criar("/api/categorias", { nome: `Roupa ${s}`, tipo: "despesa" });
  const casa = await criar("/api/categorias", { nome: `Casa ${s}`, tipo: "despesa" });
  const compra = await criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 100000,
    data: dia(-35),
    descricao: `Mercado Livre ${s}`,
    conta_id: cartao.id,
    categoria_ids: [],
    tags: [],
    partes: [
      { id: randomUUID(), descricao: "Vestido", valor_centavos: 60000, categoria_ids: [roupa.id] },
      { id: randomUUID(), descricao: "Cortina", valor_centavos: 40000, categoria_ids: [casa.id] },
    ],
  });
  await criar("/api/transferencias", { id: randomUUID(), conta_origem_id: conta.id, conta_destino_id: cartao.id, valor_centavos: 60000, data: dia(0), descricao: "Fatura", fatura_mes: compra.mes });

  await page.goto(`/#/cartoes/${cartao.id}/${compra.mes}`);
  await page.getByRole("button", { name: "Corrigir fatura" }).click();
  const correcao = page.getByRole("form", { name: "Corrigir fatura" });
  await correcao.getByRole("group", { name: /Mercado Livre/ }).getByRole("textbox").fill("900,00");
  await expect(correcao).toContainText("Pago R$ 600,00 de R$ 900,00");
  await correcao.getByRole("button", { name: "Salvar correção" }).click();
  await expect(correcao).toHaveCount(0);

  const lido = await page.request.get("/api/lancamentos", { headers });
  const atual = (await lido.json()).find((l: { id: string }) => l.id === compra.id);
  expect(atual.valor_centavos).toBe(90000);
  expect(atual.partes.map((p: { valor_centavos: number }) => p.valor_centavos)).toEqual([60000, 30000]);
});

test("a correção do valor de uma ocorrência da recorrência com partes as divide na proporção", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const visa = `Visa ${s}`;
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
  const conta = await criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const celular = await criar("/api/categorias", { nome: `Celular ${s}`, tipo: "despesa" });
  const internet = await criar("/api/categorias", { nome: `Internet ${s}`, tipo: "despesa" });
  // O combo lançado há 35 dias, no dia dele: a ocorrência nasce realizada (ticket 127).
  const regra = await criar("/api/recorrencias", {
    id: randomUUID(),
    tipo: "despesa",
    valor_centavos: 100000,
    tipo_do_valor: "estimado",
    descricao: `Combo ${s}`,
    conta_id: cartao.id,
    categoria_ids: [],
    partes: [
      { id: randomUUID(), descricao: "Celular", valor_centavos: 60000, categoria_ids: [celular.id] },
      { id: randomUUID(), descricao: "Internet", valor_centavos: 40000, categoria_ids: [internet.id] },
    ],
    inicio: dia(-35),
    dia_do_lancamento: dia(-35),
    a_cada: 1,
    unidade: "meses",
    vezes: 1,
  });
  const lidos = await (await page.request.get("/api/lancamentos", { headers })).json();
  const ocorrencia = lidos.find((l: { recorrencia_id: string }) => l.recorrencia_id === regra.id);
  expect(ocorrencia.situacao).toBe("realizado");
  await criar("/api/transferencias", { id: randomUUID(), conta_origem_id: conta.id, conta_destino_id: cartao.id, valor_centavos: 60000, data: dia(0), descricao: "Fatura", fatura_mes: ocorrencia.mes });

  await page.goto(`/#/cartoes/${cartao.id}/${ocorrencia.mes}`);
  await page.getByRole("button", { name: "Corrigir fatura" }).click();
  const correcao = page.getByRole("form", { name: "Corrigir fatura" });
  await correcao.getByRole("group", { name: /Combo/ }).getByRole("textbox").fill("900,00");
  await correcao.getByRole("button", { name: "Salvar correção" }).click();
  await expect(correcao).toHaveCount(0);

  const atual = (await (await page.request.get("/api/lancamentos", { headers })).json()).find((l: { id: string }) => l.id === ocorrencia.id);
  expect(atual.valor_centavos).toBe(90000);
  expect(atual.partes.map((p: { valor_centavos: number }) => p.valor_centavos)).toEqual([54000, 36000]);
});
