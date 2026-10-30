import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

const POR_EXTENSO = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

/** O primeiro dia do mês que vem em São Paulo, como `AAAA-MM-01`, e o dia 15 dele. */
function mesQueVem(): { mes: string; dia15: string; nome: string } {
  const [ano, mes] = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date()).split("-").map(Number);
  const [a, m] = mes === 12 ? [ano + 1, 1] : [ano, mes + 1];
  const mm = String(m).padStart(2, "0");
  return { mes: `${a}-${mm}-01`, dia15: `${a}-${mm}-15`, nome: `${POR_EXTENSO[m - 1]} de ${a}` };
}

const reais = (centavos: number) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(centavos / 100).replace(/\s/g, " ");

/** Ainda não há tela de recorrência nem de previsto avulso na aba: o teste lança pela API, com o token da página. */
async function tokenDaPagina(page: Page): Promise<string> {
  const pedido = page.waitForRequest((r) => r.url().includes("/api/") && !!r.headers().authorization);
  await page.reload();
  return (await pedido).headers().authorization;
}

test("a aba Futuro mostra o gráfico e a tabela dos próximos meses com o previsto do mês que vem", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const { mes, dia15, nome } = mesQueVem();
  await page.goto("/#/futuro");
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Futuro", level: 2 })).toBeVisible();
  const headers = { authorization: await tokenDaPagina(page) };
  const criar = async (caminho: string, data: object) => {
    const resposta = await page.request.post(caminho, { headers, data });
    expect(resposta.ok(), await resposta.text()).toBe(true);
    return resposta.json();
  };
  // O banco do teste é dividido com os outros: o que se confere é o que o previsto novo muda.
  const antes = await (await page.request.get("/api/futuro", { headers })).json();
  const linhaAntes = antes.proximos_meses.find((m: { mes: string }) => m.mes === mes);
  const conta = await criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const salario = await criar("/api/categorias", { nome: `Salário ${s}`, tipo: "receita" });
  await criar("/api/lancamentos", {
    id: randomUUID(),
    tipo: "receita",
    valor_centavos: 123456,
    data: dia15,
    descricao: `Freela ${s}`,
    conta_id: conta.id,
    categoria_ids: [salario.id],
    situacao: "previsto",
  });

  await page.reload();
  await expect(page.getByRole("region", { name: "Projeção de saldo" }).getByRole("img")).toBeVisible();
  await expect(page.getByText("Só com os previstos").first()).toBeVisible();
  const linha = page.getByRole("region", { name: "Próximos meses" }).getByRole("row", { name: new RegExp(`^${nome}`) });
  // As células: previstos, faturas, planejamento, fim só com os previstos, fim com o planejamento.
  await expect(linha.getByRole("cell").nth(3)).toHaveText(reais(linhaAntes.so_previstos_centavos + 123456));
  await expect(linha.getByRole("cell").nth(4)).toHaveText(reais(linhaAntes.com_planejamento_centavos + 123456));
});
