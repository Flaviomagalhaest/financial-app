import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./entrar";
import { cadastrar, digitar } from "./lancar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

/** Dia `deslocamento` dias a partir de hoje em São Paulo, como `AAAA-MM-DD`. */
function dia(deslocamento: number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(Date.now() + deslocamento * 86_400_000));
}

const porExtenso = (iso: string) => iso.split("-").reverse().join("/");
const linha = (page: Page, texto: string) => page.getByRole("listitem").filter({ hasText: texto });

async function prepararCasal(page: Page) {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const nomes = { s, conta: `Corrente ${s}`, cartao: `Cartão ${s}`, mercado: `Mercado ${s}`, viagem: `Viagem ${s}` };
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", nomes.conta, "corrente");
  await cadastrar(page, "Nova conta", nomes.cartao, "corrente");
  await cadastrar(page, "Nova categoria", nomes.mercado, "despesa");
  await cadastrar(page, "Nova categoria", nomes.viagem, "despesa");
  return nomes;
}

test("a folha de detalhes completa o lançamento e o resumo fica numa linha embaixo do valor", async ({ page }) => {
  const { s, conta, mercado, viagem } = await prepararCasal(page);
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();

  await digitar(page, "8", "9", "9", "0");
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: mercado }).click();
  await page.getByRole("button", { name: viagem }).click();
  const resumo = page.getByRole("button", { name: /^Detalhes/ });
  await expect(resumo).toContainText("descrição, tags, pessoa, data");

  await resumo.click();
  const folha = page.getByRole("dialog", { name: "Detalhes" });
  await folha.getByLabel("Descrição").fill(`Jantar em Paraty ${s}`);
  // Tag nova criada no próprio lançamento.
  await folha.getByLabel("Nova tag").fill(`paraty ${s}`);
  await folha.getByRole("button", { name: "Criar tag" }).click();
  await expect(folha.getByRole("button", { name: `#paraty ${s}` })).toHaveAttribute("aria-pressed", "true");
  await folha.getByRole("group", { name: "Pessoa" }).getByRole("button", { name: "Flávio" }).click();
  await folha.getByRole("button", { name: "Ontem" }).click();
  await expect(folha.getByLabel("Outra data")).toHaveValue(dia(-1));
  await expect(folha.getByRole("group", { name: "Situação" }).getByRole("button", { name: "Realizado" })).toHaveAttribute("aria-pressed", "true");
  // Parcelado e recorrente chegam com os tickets 46 e 86.
  await expect(folha.getByRole("button", { name: "Parcelado" })).toBeDisabled();
  await expect(folha.getByRole("button", { name: "Recorrente" })).toBeDisabled();
  await folha.getByRole("button", { name: "Pronto" }).click();
  await expect(folha).toHaveCount(0);
  await expect(resumo).toHaveText(`Detalhes: Jantar em Paraty ${s} · #paraty ${s} · Flávio · ontem`);

  await page.getByRole("button", { name: "Salvar" }).click();
  const jantar = linha(page, `Jantar em Paraty ${s}`);
  await expect(jantar).toContainText("− R$ 89,90");
  await expect(jantar).toContainText(`${porExtenso(dia(-1))} · ${conta} · `);
  await expect(jantar).toContainText(mercado);
  await expect(jantar).toContainText(viagem);
  await expect(jantar).toContainText(`#paraty ${s}`);
  await expect(jantar).toContainText("Flávio");
  await expect(jantar).not.toContainText("previsto");

  // A tag criada vira opção do próximo lançamento, e a data futura nasce prevista, trocável à mão.
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, "1", "00");
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: mercado }).click();
  await resumo.click();
  await folha.getByLabel("Descrição").fill(`IPVA ${s}`);
  await folha.getByLabel("Outra data").fill(dia(10));
  await expect(folha.getByRole("group", { name: "Situação" }).getByRole("button", { name: "Previsto" })).toHaveAttribute("aria-pressed", "true");
  await expect(folha.getByRole("button", { name: `#paraty ${s}` })).toHaveAttribute("aria-pressed", "false");
  await folha.getByRole("button", { name: "Pronto" }).click();
  await expect(resumo).toHaveText(`Detalhes: IPVA ${s} · ${porExtenso(dia(10))} · previsto`);
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(linha(page, `IPVA ${s}`)).toContainText("previsto");

  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await digitar(page, "2", "00");
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: mercado }).click();
  await resumo.click();
  await folha.getByLabel("Descrição").fill(`Conta que devo ${s}`);
  await folha.getByRole("button", { name: "Hoje" }).click();
  await folha.getByRole("group", { name: "Situação" }).getByRole("button", { name: "Previsto" }).click();
  await folha.getByRole("button", { name: "Pronto" }).click();
  await expect(resumo).toHaveText(`Detalhes: Conta que devo ${s} · previsto`);
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(linha(page, `Conta que devo ${s}`)).toContainText(`${porExtenso(dia(0))} · ${conta}`);
  await expect(linha(page, `Conta que devo ${s}`)).toContainText("previsto");
});

test("'Repetir último' aparece enquanto o lançamento está vazio e lança de novo o mesmo, com a data de hoje", async ({ page }) => {
  const { s, conta, cartao, mercado, viagem } = await prepararCasal(page);
  await page.goto("/#/novo");
  await digitar(page, "4", "5", "0", "0");
  await page.getByRole("button", { name: cartao }).click();
  await page.getByRole("button", { name: viagem }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  const folha = page.getByRole("dialog", { name: "Detalhes" });
  await folha.getByLabel("Descrição").fill(`Pedágio ${s}`);
  await folha.getByLabel("Nova tag").fill(`viagem ${s}`);
  await folha.getByRole("button", { name: "Criar tag" }).click();
  await folha.getByRole("group", { name: "Pessoa" }).getByRole("button", { name: "Flávio" }).click();
  await folha.getByRole("button", { name: "Ontem" }).click();
  await folha.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(linha(page, `Pedágio ${s}`)).toHaveCount(1);

  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  const repetir = page.getByRole("button", { name: /^Repetir último/ });
  await expect(repetir).toHaveText(`Repetir último: Pedágio ${s}, R$ 45,00 · ${viagem} · ${cartao}`);
  // Com o lançamento começado, some.
  await digitar(page, "1");
  await expect(repetir).toHaveCount(0);
  await digitar(page, "Apagar");
  await page.getByRole("button", { name: mercado }).click();
  await expect(repetir).toHaveCount(0);
  await page.getByRole("button", { name: mercado }).click();

  await repetir.click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 45,00");
  await expect(page.getByRole("button", { name: cartao })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: viagem, exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: /^Detalhes/ })).toHaveText(`Detalhes: Pedágio ${s} · #viagem ${s} · Flávio`);
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(linha(page, `Pedágio ${s}`)).toHaveCount(2);
  await expect(linha(page, `Pedágio ${s}`).first()).toContainText(`${porExtenso(dia(0))} · ${cartao} · ${viagem} · #viagem ${s}`);
});

test("transferência entre duas contas, com categoria opcional, move o saldo e precisa de internet", async ({ page, context }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [corrente, poupanca, reserva] = [`Corrente ${s}`, `Poupança ${s}`, `Reserva ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  await cadastrar(page, "Nova conta", corrente, "corrente");
  await cadastrar(page, "Nova conta", poupanca, "poupanca");
  await cadastrar(page, "Nova categoria", reserva, "transferencia");

  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await page.getByRole("group", { name: "Tipo" }).getByRole("button", { name: "Transferência" }).click();
  await expect(page.getByRole("heading", { name: "Nova transferência", level: 2 })).toBeVisible();
  const salvar = page.getByRole("button", { name: "Salvar" });
  await digitar(page, "2", "5", "0", "00");
  await expect(page.getByTestId("valor")).toHaveText("R$ 250,00");
  await page.getByRole("group", { name: "De" }).getByRole("button", { name: corrente }).click();
  // A conta de origem não aparece no destino.
  await expect(page.getByRole("group", { name: "Para" }).getByRole("button", { name: corrente })).toHaveCount(0);
  await expect(salvar).toBeDisabled();
  await page.getByRole("group", { name: "Para" }).getByRole("button", { name: poupanca }).click();
  await expect(salvar).toBeEnabled();
  await page.getByRole("group", { name: "Categoria (opcional)" }).getByRole("button", { name: reserva }).click();
  await page.getByLabel("Descrição").fill(`Guardar ${s}`);
  await salvar.click();

  await expect(page.getByRole("heading", { name: "Hoje", level: 2 })).toBeVisible();
  await page.goto("/#/contas-e-categorias");
  await expect(linha(page, corrente)).toContainText("R$ 250,00");
  await expect(linha(page, corrente)).toContainText("-");
  await expect(linha(page, poupanca)).toContainText("R$ 250,00");
  await expect(linha(page, poupanca)).not.toContainText("-");

  // Sem internet, a tela avisa e não salva (ADR 0011: só lançamentos funcionam sem internet).
  await context.setOffline(true);
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await page.getByRole("group", { name: "Tipo" }).getByRole("button", { name: "Transferência" }).click();
  await expect(page.getByText("Sem internet: a transferência precisa de internet.")).toBeVisible();
  await digitar(page, "1", "00");
  await page.getByRole("group", { name: "De" }).getByRole("button", { name: corrente }).click();
  await page.getByRole("group", { name: "Para" }).getByRole("button", { name: poupanca }).click();
  await expect(salvar).toBeDisabled();
  // Voltar para despesa leva ao lançamento comum, que funciona sem internet.
  await page.getByRole("group", { name: "Tipo" }).getByRole("button", { name: "Despesa" }).click();
  await expect(page.getByRole("heading", { name: "Novo lançamento", level: 2 })).toBeVisible();
});

test("sem internet, o atalho do ícone abre o novo lançamento e a jornada inteira vai para a fila", async ({ page, context }) => {
  const { s, conta, mercado } = await prepararCasal(page);
  // Instalado: o service worker controla a página a partir da próxima abertura.
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
  await page.goto("/#/historico");
  await expect(page.getByRole("heading", { name: "Histórico", level: 2 })).toBeVisible();

  await context.setOffline(true);
  // O atalho "Novo lançamento" do Android abre `/#/novo` direto.
  await page.goto("/#/novo");
  await expect(page.getByRole("heading", { name: "Novo lançamento", level: 2 })).toBeVisible();
  await digitar(page, "1", "8", "5", "0");
  await expect(page.getByTestId("valor")).toHaveText("R$ 18,50");
  await page.getByRole("button", { name: conta }).click();
  await page.getByRole("button", { name: mercado }).click();
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  const folha = page.getByRole("dialog", { name: "Detalhes" });
  await folha.getByLabel("Descrição").fill(`Padaria ${s}`);
  await folha.getByLabel("Nova tag").fill(`café ${s}`);
  await folha.getByRole("button", { name: "Criar tag" }).click();
  await folha.getByRole("button", { name: "Ontem" }).click();
  await folha.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  const padarias = linha(page, `Padaria ${s}`);
  await expect(padarias).toContainText("⏳ não enviado");
  await expect(padarias).toContainText(`${porExtenso(dia(-1))} · ${conta} · ${mercado} · #café ${s}`);

  // O não enviado também é o último para repetir, e a tag criada sem internet já é opção.
  await page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: "Hoje" }).click();
  await page.getByRole("link", { name: "+ Novo lançamento" }).click();
  await page.getByRole("button", { name: /^Repetir último/ }).click();
  await expect(page.getByTestId("valor")).toHaveText("R$ 18,50");
  await page.getByRole("button", { name: /^Detalhes/ }).click();
  await expect(folha.getByRole("button", { name: `#café ${s}` })).toHaveAttribute("aria-pressed", "true");
  await folha.getByRole("button", { name: "Pronto" }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(padarias).toHaveCount(2);

  await context.setOffline(false);
  await expect(padarias.first()).not.toContainText("não enviado");
  await expect(padarias.last()).not.toContainText("não enviado");
  await page.reload();
  await expect(padarias).toHaveCount(2);
  await expect(padarias.first()).toContainText(`${porExtenso(dia(0))} · ${conta} · ${mercado} · #café ${s}`);
  await expect(padarias.last()).toContainText(`${porExtenso(dia(-1))} · ${conta} · ${mercado} · #café ${s}`);
});
