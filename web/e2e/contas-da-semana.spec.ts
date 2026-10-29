import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

/** Dia `deslocamento` dias a partir de hoje em São Paulo, como `AAAA-MM-DD`. */
function dia(deslocamento: number): string {
  const data = new Date(Date.now() + deslocamento * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(data);
}

const porExtenso = (iso: string) => iso.split("-").reverse().join("/");

const digitar = async (page: Page, ...teclas: string[]) => {
  for (const tecla of teclas) await page.getByRole("button", { name: tecla, exact: true }).click();
};

async function cadastrar(page: Page, formulario: string, nome: string, tipo: string) {
  const form = page.getByRole("form", { name: formulario });
  await form.getByLabel("Nome").fill(nome);
  await form.getByLabel("Tipo").selectOption(tipo);
  await form.getByRole("button", { name: "Cadastrar" }).click();
  await expect(page.getByRole("listitem").filter({ hasText: nome })).toBeVisible();
}

type Previsto = { tipo: "Despesa" | "Receita"; teclas: string[]; categoria: string; descricao: string; data: string; previsto?: boolean };

async function lancar(page: Page, conta: string, l: Previsto) {
  await page.goto("/#/novo");
  await page.getByRole("button", { name: l.tipo, exact: true }).click();
  await digitar(page, ...l.teclas);
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: l.categoria }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await page.getByLabel("Descrição").fill(l.descricao);
  await page.getByLabel("Data").fill(l.data);
  // Conta que devo e ainda não paguei: data passada, mas previsto à mão.
  if (l.previsto) await page.getByRole("button", { name: "Previsto", exact: true }).click();
  await page.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();
}

test("confirma as contas da semana em um toque ou ajustando, e só o realizado mexe no saldo", async ({ page }) => {
  const s = String(Date.now());
  const [conta, luz, salario] = [`Corrente ${s}`, `Luz ${s}`, `Salário ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", luz, "despesa");
  await cadastrar(page, "Nova categoria", salario, "receita");

  await lancar(page, conta, { tipo: "Despesa", teclas: ["7", "0", "00"], categoria: luz, descricao: `Conta de luz ${s}`, data: dia(-1), previsto: true });
  await lancar(page, conta, { tipo: "Receita", teclas: ["5", "0", "00", "00"], categoria: salario, descricao: `Pagamento ${s}`, data: dia(3) });
  await lancar(page, conta, { tipo: "Despesa", teclas: ["9", "00"], categoria: luz, descricao: `IPVA ${s}`, data: dia(20) });

  // Na lista, o previsto com data passada aparece como atrasado.
  const luzNaLista = page.getByRole("listitem").filter({ hasText: `Conta de luz ${s}` });
  await expect(luzNaLista).toContainText("atrasado");
  await expect(page.getByRole("listitem").filter({ hasText: `Pagamento ${s}` })).toContainText("previsto");

  // Previsto não mexe no saldo.
  await page.goto("/#/contas-e-categorias");
  const saldo = page.getByRole("listitem").filter({ hasText: conta });
  await expect(saldo).toContainText("R$ 0,00");

  // Na Hoje: atrasados e os próximos 7 dias, em ordem de data; o de daqui a 20 dias fica de fora.
  await page.goto("/#/hoje");
  const bloco = page.getByRole("region", { name: "Contas da semana" });
  const minhas = bloco.getByRole("listitem").filter({ hasText: s });
  await expect(bloco).toContainText(/\d+ contas? da semana para confirmar/);
  await expect(minhas).toHaveCount(2);
  await expect(minhas.nth(0)).toContainText(`Conta de luz ${s}`);
  await expect(minhas.nth(0)).toContainText("atrasado");
  await expect(minhas.nth(0)).toContainText("− R$ 70,00");
  await expect(minhas.nth(1)).toContainText(`Pagamento ${s}`);
  await expect(minhas.nth(1)).toContainText(porExtenso(dia(3)));
  await expect(bloco).not.toContainText(`IPVA ${s}`);
  const quantas = async () => Number((await bloco.getByTestId("quantas-contas").textContent())?.match(/\d+/)?.[0]);
  const antes = await quantas();

  // Confirmar em um toque: sai da lista e a contagem cai.
  await bloco.getByRole("button", { name: `Confirmar Conta de luz ${s}` }).click();
  await expect(minhas).toHaveCount(1);
  await expect.poll(quantas).toBe(antes - 1);

  // Ajustar: o salário veio diferente e caiu hoje.
  await bloco.getByRole("button", { name: `Ajustar Pagamento ${s}` }).click();
  const ajuste = bloco.getByRole("group", { name: `Ajuste de Pagamento ${s}` });
  await expect(ajuste.getByTestId("valor")).toHaveText("R$ 5.000,00");
  await digitar(page, ...Array(6).fill("Apagar"), "5", "1", "2", "3", "4", "5");
  await expect(ajuste.getByTestId("valor")).toHaveText("R$ 5.123,45");
  await ajuste.getByLabel("Data").fill(dia(0));
  await ajuste.getByRole("button", { name: "Confirmar com ajuste" }).click();
  await expect(minhas).toHaveCount(0);

  // Confirmados viram realizados e entram no saldo: 5.123,45 − 70,00.
  await page.goto("/#/contas-e-categorias");
  await expect(saldo).toContainText("R$ 5.053,45");
  await page.goto("/#/historico");
  const pagamento = page.getByRole("listitem").filter({ hasText: `Pagamento ${s}` });
  await expect(pagamento).toContainText(porExtenso(dia(0)));
  await expect(pagamento).not.toContainText("previsto");
  await expect(luzNaLista).not.toContainText("atrasado");
});
