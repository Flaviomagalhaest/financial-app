import { expect, test, type Page } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { cadastrar } from "./lancar";

// Ticket 97: arquivar não mexe na recorrência; o app avisa antes e lembra depois, enquanto ela gerar ali.
test.use({ timezoneId: "America/Sao_Paulo" });

const linha = (page: Page, nome: string) => page.getByRole("listitem").filter({ hasText: nome }).first();
/** Daqui a `dias` dias em São Paulo (`AAAA-MM-DD`). */
const daquiA = (dias: number) => new Date(Date.now() + dias * 86_400_000).toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });
const porExtenso = (iso: string) => iso.split("-").reverse().join("/");

test("arquivar conta, cartão ou categoria com recorrência ativa avisa antes e lembra depois", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const [itau, nubank, sem, casa, cartao, luz, streaming] = [`Itaú ${s}`, `Nubank ${s}`, `Sem regra ${s}`, `Casa ${s}`, `Cartão ${s}`, `Luz ${s}`, `Streaming ${s}`];
  await page.goto("/#/contas-e-categorias");
  await entrar(page);
  for (const conta of [itau, nubank, sem]) await cadastrar(page, "Nova conta", conta, "corrente");
  await cadastrar(page, "Nova categoria", casa, "despesa");
  const api = await apiDaPagina(page);
  const contaId = (nome: string) => api.ler("/api/contas").then((cs) => cs.find((c: { nome: string }) => c.nome === nome).id);
  const casaId = (await api.ler("/api/categorias")).find((c: { nome: string }) => c.nome === casa).id;
  const cartaoId = (
    await api.criar("/api/cartoes", { nome: cartao, titular_id: null, dia_fechamento: 1, dia_vencimento: 10, limite_centavos: null, mes_anterior_ao_fechamento: false })
  ).id;
  const regra = (descricao: string, conta: string) => ({
    id: crypto.randomUUID(),
    tipo: "despesa",
    valor_centavos: 18990,
    tipo_do_valor: "estimado",
    descricao,
    conta_id: conta,
    categoria_ids: [casaId],
    inicio: daquiA(5),
    a_cada: 1,
    unidade: "meses",
    vezes: 3,
  });
  const regraDaLuz = await api.criar("/api/recorrencias", regra(luz, await contaId(itau)));
  await api.criar("/api/recorrencias", regra(streaming, cartaoId));
  await page.reload();

  // Sem recorrência, o arquivamento segue direto, como antes.
  await page.getByRole("button", { name: `Arquivar conta ${sem}` }).click();
  await expect(linha(page, sem)).toContainText("(arquivada)");

  // Com recorrência ativa, vem o aviso; cancelar não arquiva.
  await page.getByRole("button", { name: `Arquivar conta ${itau}` }).click();
  const aviso = page.getByRole("group", { name: `Arquivar ${itau}` });
  await expect(aviso).toContainText(`1 recorrência ativa usa a conta ${itau}`);
  await expect(aviso.getByRole("link", { name: `${luz}, próxima em ${porExtenso(daquiA(5))}` })).toBeVisible();
  await aviso.getByRole("button", { name: "Cancelar" }).click();
  await expect(aviso).toHaveCount(0);
  await expect(linha(page, itau)).not.toContainText("(arquivada)");

  // Arquivar mesmo assim: a linha da conta lembra a recorrência, que abre pela tela dela.
  await page.getByRole("button", { name: `Arquivar conta ${itau}` }).click();
  await aviso.getByRole("button", { name: "Arquivar mesmo assim" }).click();
  await expect(linha(page, itau)).toContainText("(arquivada)");
  const lembrete = page.getByRole("group", { name: `Recorrências ativas em ${itau}` });
  await expect(lembrete).toContainText("1 recorrência ativa segue gerando previstos aqui");
  await lembrete.getByRole("link", { name: new RegExp(luz) }).click();
  await expect(page.getByRole("heading", { name: "Recorrência", level: 2 })).toBeVisible();
  await expect(page.getByLabel("Conta ou cartão").locator("option:checked")).toHaveText(`${itau} (arquivada)`);

  // A categoria avisa pelas duas regras; o cartão, pela dele.
  await page.goto("/#/contas-e-categorias");
  await page.getByRole("button", { name: `Arquivar ${casa}` }).click();
  await expect(page.getByRole("group", { name: `Arquivar ${casa}` })).toContainText(`2 recorrências ativas usam a categoria ${casa}`);
  await page.getByRole("group", { name: `Arquivar ${casa}` }).getByRole("button", { name: "Arquivar mesmo assim" }).click();
  await expect(page.getByRole("group", { name: `Recorrências ativas em ${casa}` })).toContainText("2 recorrências ativas seguem gerando previstos aqui");
  await page.getByRole("button", { name: `Arquivar cartão ${cartao}` }).click();
  await expect(page.getByRole("group", { name: `Arquivar ${cartao}` })).toContainText(`1 recorrência ativa usa o cartão ${cartao}`);
  await page.getByRole("group", { name: `Arquivar ${cartao}` }).getByRole("button", { name: "Arquivar mesmo assim" }).click();
  await expect(linha(page, cartao)).toContainText("(arquivado)");

  // Trocar a conta daqui para frente tira a regra do lembrete; desarquivar não a traz de volta.
  await api.mudar(`/api/recorrencias/${regraDaLuz.id}`, { a_partir_da_ocorrencia: 1, conta_id: await contaId(nubank) });
  await page.reload();
  await expect(linha(page, itau)).toContainText("(arquivada)");
  await expect(page.getByRole("group", { name: `Recorrências ativas em ${itau}` })).toHaveCount(0);
  await page.getByRole("button", { name: `Desarquivar conta ${itau}` }).click();
  await expect(linha(page, itau)).not.toContainText("(arquivada)");
  expect((await api.ler("/api/recorrencias")).find((r: { id: string }) => r.id === regraDaLuz.id).conta_id).toBe(await contaId(nubank));
});
