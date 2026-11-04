import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

const hoje = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());

/** O dia 10 do mês `deslocamento` meses depois (ou antes, se negativo) do atual. */
function mesDeslocado(deslocamento: number) {
  const [ano, mes] = hoje().split("-").map(Number);
  const d = new Date(Date.UTC(ano, mes - 1 + deslocamento, 10));
  return { data: d.toISOString().slice(0, 10), rotulo: `${String(d.getUTCMonth() + 1).padStart(2, "0")}/${d.getUTCFullYear()}` };
}

/** Uma conta e uma categoria criadas pela API, o Histórico aberto e `lancar` para pôr um lançamento numa data. */
async function preparar(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/historico");
  await entrar(page);
  const api = await apiDaPagina(page);
  const conta = await api.criar("/api/contas", { nome: `Corrente ${s}`, tipo: "corrente" });
  const categoria = await api.criar("/api/categorias", { nome: `Mercado ${s}`, tipo: "despesa" });
  const lancar = (descricao: string, data: string) =>
    api.criar("/api/lancamentos", { id: randomUUID(), tipo: "despesa", valor_centavos: 4500, data, descricao: `${descricao} ${s}`, conta_id: conta.id, categoria_ids: [categoria.id] });
  const linha = (descricao: string) => page.getByRole("listitem").filter({ hasText: `${descricao} ${s}` });
  return { s, lancar, linha };
}

/** Rola até o fim da tela até `visivel` aparecer: cada chegada ao fim desenha mais um mês. */
async function rolarAte(page: Page, visivel: ReturnType<Page["locator"]>) {
  await expect(async () => {
    await page.getByTestId("fim-da-lista").scrollIntoViewIfNeeded();
    await expect(visivel).toBeVisible({ timeout: 1000 });
  }).toPass({ timeout: 45_000 });
}

test("o Histórico se desenha mês a mês, com cabeçalho de mês, e desenha o mês anterior quando a pessoa chega ao fim da tela", async ({ page }) => {
  const { lancar, linha } = await preparar(page);
  // Uma tela pequena: o fim da lista não aparece sozinho antes de a pessoa rolar.
  await page.setViewportSize({ width: 390, height: 500 });
  const meses = [0, -1, -2, -3, -4].map(mesDeslocado);
  for (const [i, m] of meses.entries()) await lancar(`Compra ${i}`, m.data);
  await page.reload();

  // Só os meses mais recentes foram desenhados: o quinto mês para trás ainda não.
  await expect(page.getByRole("heading", { level: 3, name: meses[0].rotulo })).toBeVisible();
  await expect(linha("Compra 4")).toHaveCount(0);

  await rolarAte(page, linha("Compra 4"));
  await expect(page.getByRole("heading", { level: 3, name: meses[4].rotulo })).toBeVisible();
});

test("depois do fim da janela do aparelho, com internet, o Histórico continua lendo do servidor mês a mês, sem guardar", async ({ page, context }) => {
  const { lancar, linha } = await preparar(page);
  const antigo = mesDeslocado(-26);
  await lancar("Geladeira", antigo.data);
  await lancar("Padaria", hoje());
  await page.reload();
  await expect(linha("Padaria")).toBeVisible();
  await expect(linha("Geladeira")).toHaveCount(0);

  await rolarAte(page, linha("Geladeira"));
  await expect(page.getByRole("heading", { level: 3, name: antigo.rotulo })).toBeVisible();

  // Não ficou no aparelho: recarregado e sem internet, ele não está lá.
  await page.reload();
  await expect(linha("Padaria")).toBeVisible();
  await context.setOffline(true);
  // Chegou ao fim da janela sem internet (o aviso prova que a leitura foi tentada) e o lido antes não ficou.
  await rolarAte(page, page.getByText(/^Para ver antes de .*, conecte-se à internet/));
  await expect(linha("Geladeira")).toHaveCount(0);
  await context.setOffline(false);
});

test("sem internet, o fim da janela diz que é preciso internet para ver antes", async ({ page, context }) => {
  const { lancar, linha } = await preparar(page);
  await lancar("Padaria", hoje());
  await page.reload();
  await expect(linha("Padaria")).toBeVisible();

  await context.setOffline(true);
  const fimDaJanela = mesDeslocado(-11).rotulo;
  const aviso = page.getByText(`Para ver antes de ${fimDaJanela}, conecte-se à internet`);
  await rolarAte(page, aviso);

  // A rede volta: o aviso sai e o Histórico continua pelo servidor.
  await context.setOffline(false);
  await expect(aviso).toHaveCount(0);
});
