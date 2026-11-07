import { expect, test } from "@playwright/test";
import { apiDaPagina } from "./api";
import { entrar } from "./entrar";
import { digitar } from "./lancar";

// O dia do casal é o de São Paulo, como na API.
test.use({ timezoneId: "America/Sao_Paulo" });

const amanha = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date(Date.now() + 86_400_000));

test("a compra à vista com partes prevista confirma com o mesmo valor, mas não com outro (ticket 156)", async ({ page }) => {
  const s = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/#/hoje");
  await entrar(page);
  const api = await apiDaPagina(page);
  const conta = await api.criar("/api/contas", { nome: `Conta ${s}`, tipo: "corrente" });
  const roupa = await api.criar("/api/categorias", { nome: `Roupa ${s}`, tipo: "despesa" });
  const casa = await api.criar("/api/categorias", { nome: `Casa ${s}`, tipo: "despesa" });
  const descricao = `Mercado Livre ${s}`;
  await api.criar("/api/lancamentos", {
    id: crypto.randomUUID(),
    tipo: "despesa",
    valor_centavos: 10000,
    data: amanha(),
    descricao,
    conta_id: conta.id,
    categoria_ids: [],
    situacao: "previsto",
    partes: [
      { id: crypto.randomUUID(), descricao: "Camisa", valor_centavos: 6000, categoria_ids: [roupa.id], tags: [] },
      { id: crypto.randomUUID(), descricao: "Toalha", valor_centavos: 4000, categoria_ids: [casa.id], tags: [] },
    ],
  });
  await page.reload();

  const bloco = page.getByRole("region", { name: "Contas da semana" });
  const linha = bloco.getByRole("listitem").filter({ hasText: descricao });
  await expect(linha).toHaveCount(1);

  // Outro valor: o botão fica desligado e a tela manda editar as partes.
  await bloco.getByRole("button", { name: `Ajustar ${descricao}` }).click();
  const ajuste = bloco.getByRole("group", { name: `Ajuste de ${descricao}` });
  await digitar(page, "Apagar");
  await expect(ajuste).toContainText("editando as partes");
  await expect(ajuste.getByRole("button", { name: "Confirmar com ajuste" })).toBeDisabled();

  // Voltando ao valor da compra, confirma.
  await digitar(page, "0");
  await expect(ajuste).not.toContainText("editando as partes");
  await ajuste.getByRole("button", { name: "Confirmar com ajuste" }).click();
  await expect(linha).toHaveCount(0);
});
