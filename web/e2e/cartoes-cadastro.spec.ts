import { expect, test } from "@playwright/test";
import { tokenDaPagina } from "./api";
import { entrar } from "./entrar";

test("cadastra um cartão titular e um adicional ligado a ele, que não tem dias nem limite próprios", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [titular, adicional] = [`Visa ${s}`, `Visa da esposa ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);

  const novo = page.getByRole("form", { name: "Novo cartão" });
  await novo.getByLabel("Nome").fill(titular);
  await novo.getByLabel("Dia de fechamento").fill("10");
  await novo.getByLabel("Dia de vencimento").fill("20");
  await novo.getByLabel("Limite (opcional)").fill("5.000,00");
  await novo.getByLabel("Conta no mês anterior ao fechamento").check();
  await novo.getByRole("button", { name: "Cadastrar cartão" }).click();

  const linha = page.getByRole("listitem").filter({ hasText: titular });
  await expect(linha).toContainText("fecha dia 10");
  await expect(linha).toContainText("vence dia 20");
  await expect(linha).toContainText("R$ 5.000,00");

  // Ligado a um titular, o cartão perde os campos de dia e de limite.
  await novo.getByLabel("Titular").selectOption({ label: titular });
  await expect(novo.getByLabel("Dia de fechamento")).toHaveCount(0);
  await expect(novo.getByLabel("Limite (opcional)")).toHaveCount(0);
  await novo.getByLabel("Nome").fill(adicional);
  await novo.getByRole("button", { name: "Cadastrar cartão" }).click();
  const filho = page.getByRole("listitem").filter({ hasText: adicional });
  await expect(filho).toContainText(`adicional de ${titular}`);

  const token = await tokenDaPagina(page);
  const resposta = await page.request.get("/api/cartoes", { headers: { authorization: token } });
  const cartoes = (await resposta.json()) as { nome: string; dia_fechamento: number | null; limite_centavos: number | null; mes_anterior_ao_fechamento: boolean }[];
  expect(cartoes.find((c) => c.nome === titular)).toMatchObject({ dia_fechamento: 10, limite_centavos: 500000, mes_anterior_ao_fechamento: true });
  expect(cartoes.find((c) => c.nome === adicional)).toMatchObject({ dia_fechamento: null, limite_centavos: null });
});

test("edita os dias padrão do cartão com o aviso das faturas, e arquiva e desarquiva", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const nome = `Nubank ${s}`;
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  const headers = { authorization: await tokenDaPagina(page) };
  const criado = await page.request.post("/api/cartoes", { headers, data: { nome, dia_fechamento: 10, dia_vencimento: 20 } });
  expect(criado.ok()).toBe(true);
  await page.reload();

  await page.getByRole("button", { name: `Editar cartão ${nome}` }).click();
  const edicao = page.getByRole("form", { name: `Editar cartão ${nome}` });
  await expect(edicao).toContainText("só as faturas abertas e futuras mudam");
  await expect(edicao).toContainText("as compras delas vão para a fatura certa");
  await edicao.getByLabel(`Dia de fechamento de ${nome}`).fill("5");
  await edicao.getByLabel(`Dia de vencimento de ${nome}`).fill("15");
  await edicao.getByLabel(`Limite de ${nome}`).fill("1.200,50");
  await edicao.getByRole("button", { name: "Salvar cartão" }).click();
  const linha = page.getByRole("listitem").filter({ hasText: nome });
  await expect(linha).toContainText("fecha dia 5");
  await expect(linha).toContainText("vence dia 15");
  await expect(linha).toContainText("R$ 1.200,50");

  await page.getByRole("button", { name: `Arquivar cartão ${nome}` }).click();
  await expect(linha).toContainText("(arquivado)");
  const ativos = await (await page.request.get("/api/cartoes", { headers })).json();
  expect(ativos.map((c: { nome: string }) => c.nome)).not.toContain(nome);
  await page.getByRole("button", { name: `Desarquivar cartão ${nome}` }).click();
  await expect(linha).not.toContainText("(arquivado)");
});

const maisDias = (iso: string, dias: number) => new Date(Date.parse(`${iso}T00:00:00Z`) + dias * 86_400_000).toISOString().slice(0, 10);

test("acerta o fechamento e o vencimento de uma fatura existente e de outra escolhida pelo mês, com o aviso de redistribuição", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const nome = `Inter ${s}`;
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  const headers = { authorization: await tokenDaPagina(page) };
  const criar = async (caminho: string, data: object) => {
    const resposta = await page.request.post(caminho, { headers, data });
    expect(resposta.ok(), await resposta.text()).toBe(true);
    return resposta.json();
  };
  const cartao = await criar("/api/cartoes", { nome, dia_fechamento: 10, dia_vencimento: 20 });
  const categoria = await criar("/api/categorias", { nome: `Mercado ${s}`, tipo: "despesa" });
  const hoje = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
  await criar("/api/lancamentos", {
    id: crypto.randomUUID(), tipo: "despesa", valor_centavos: 2500, data: hoje, descricao: `Padaria ${s}`,
    conta_id: cartao.id, categoria_ids: [categoria.id], tags: [],
  });
  const faturas = async () => (await (await page.request.get(`/api/cartoes/${cartao.id}/faturas`, { headers })).json()) as { mes: string; fechamento: string; vencimento: string }[];
  const [nascida] = await faturas();
  await page.reload();

  await page.getByRole("button", { name: `Acertar fatura de ${nome}` }).click();
  const form = page.getByRole("form", { name: `Acertar fatura de ${nome}` });
  await expect(form).toContainText("as compras delas se redistribuem");
  await form.getByLabel("Fatura").selectOption(nascida.mes);
  await expect(form.getByLabel("Fechamento")).toHaveValue(nascida.fechamento);
  await form.getByLabel("Fechamento").fill(maisDias(nascida.fechamento, 1));
  await form.getByLabel("Vencimento").fill(maisDias(nascida.vencimento, 1));
  await form.getByRole("button", { name: "Salvar fatura" }).click();
  await expect(form).toHaveCount(0);
  const [acertada] = await faturas();
  expect(acertada).toMatchObject({ mes: nascida.mes, fechamento: maisDias(nascida.fechamento, 1), vencimento: maisDias(nascida.vencimento, 1) });

  // Uma fatura que ainda não nasceu: escolhe o mês e ela nasce com as datas informadas.
  const [ano, mes] = nascida.mes.split("-").map(Number);
  const futuro = new Date(Date.UTC(ano, mes - 1 + 3, 1)).toISOString().slice(0, 7);
  await page.getByRole("button", { name: `Acertar fatura de ${nome}` }).click();
  await form.getByLabel("Fatura").selectOption("outro");
  await form.getByLabel("Mês da fatura").fill(futuro);
  await form.getByLabel("Fechamento").fill(`${futuro}-12`);
  await form.getByLabel("Vencimento").fill(`${futuro}-22`);
  await form.getByRole("button", { name: "Salvar fatura" }).click();
  await expect(form).toHaveCount(0);
  expect((await faturas()).find((f) => f.mes === `${futuro}-01`)).toMatchObject({ fechamento: `${futuro}-12`, vencimento: `${futuro}-22` });
});
