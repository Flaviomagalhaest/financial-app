// O cálculo puro do aviso de planejamento (ticket 52), por tabela e sem navegador: o mesmo que a
// tela de lançar roda sobre o planejamento guardado e a fila.
import { expect, test } from "@playwright/test";
import { avisoDePlanejamento, avisosDasPartes, comAFila, mesEmQueConta, oQueSobra, semContarDeNovo, ultimaEscolha, type Contagem, type Planejamento } from "../src/dados/aviso";

const OUT = "2026-10-01";
const NOV = "2026-11-01";

/** Outubro: Mercado em 82% (sobram R$ 180), Casa em 30% (R$ 100 realizado e R$ 50 previsto). */
const outubro: Planejamento = {
  mes: "2026-10",
  itens: [
    { id: "i-mercado", categoria_id: "mercado", planejado_centavos: 100000, realizado_centavos: 82000, previsto_centavos: 0, percentual: 82, ainda_da_para_gastar_centavos: 18000 },
    { id: "i-casa", categoria_id: "casa", planejado_centavos: 50000, realizado_centavos: 10000, previsto_centavos: 5000, percentual: 30, ainda_da_para_gastar_centavos: 35000 },
  ],
  a_escolher: [],
  ainda_da_para_gastar_centavos: 53000,
  ajustes_de_fatura_centavos: 0,
};

/** O mesmo outubro com um lançamento a escolher que ficou no Mercado. */
const comAEscolher: Planejamento = { ...outubro, a_escolher: [{ lancamento_id: "ambiguo", item_categoria_id: "mercado", categorias_com_item: ["casa", "mercado"] }] };

const lancamento = (campos: Partial<Contagem>): Contagem => ({ id: "novo", valor_centavos: 0, categoria_ids: ["mercado"], situacao: "realizado", mes: OUT, ...campos });

const estado = (percentual: number, ainda: number) => ({ percentual, ainda_da_para_gastar_centavos: ainda });

test.describe("aviso de planejamento", () => {
  const casos: { caso: string; planejamento?: Planejamento; antes?: Contagem; depois: Contagem; aviso: ReturnType<typeof avisoDePlanejamento> }[] = [
    {
      caso: "a despesa nova estoura o item: 82% → 105%, passa R$ 50",
      depois: lancamento({ valor_centavos: 23000 }),
      aviso: { mes: OUT, categoriasComItem: ["mercado"], aEscolher: false, item: { categoria_id: "mercado", planejado_centavos: 100000, antes: estado(82, 18000), depois: estado(105, -5000) } },
    },
    {
      caso: "o previsto também conta",
      depois: lancamento({ valor_centavos: 5000, categoria_ids: ["casa"], situacao: "previsto" }),
      aviso: { mes: OUT, categoriasComItem: ["casa"], aEscolher: false, item: { categoria_id: "casa", planejado_centavos: 50000, antes: estado(30, 35000), depois: estado(40, 30000) } },
    },
    {
      caso: "nenhuma categoria com item: conta só no total do mês",
      depois: lancamento({ valor_centavos: 5000, categoria_ids: ["lazer"] }),
      aviso: { mes: OUT, categoriasComItem: [], aEscolher: false, item: null },
    },
    {
      caso: "a categoria sem item ao lado da com item não muda nada",
      depois: lancamento({ valor_centavos: 5000, categoria_ids: ["lazer", "casa"] }),
      aviso: { mes: OUT, categoriasComItem: ["casa"], aEscolher: false, item: { categoria_id: "casa", planejado_centavos: 50000, antes: estado(30, 35000), depois: estado(40, 30000) } },
    },
    {
      caso: "duas com item: conta na escolhida",
      depois: lancamento({ valor_centavos: 5000, categoria_ids: ["mercado", "casa"], item_categoria_id: "casa" }),
      aviso: { mes: OUT, categoriasComItem: ["mercado", "casa"], aEscolher: false, item: { categoria_id: "casa", planejado_centavos: 50000, antes: estado(30, 35000), depois: estado(40, 30000) } },
    },
    {
      caso: "duas com item e sem escolha: a escolher, sem item",
      depois: lancamento({ valor_centavos: 5000, categoria_ids: ["casa", "mercado"] }),
      aviso: { mes: OUT, categoriasComItem: ["casa", "mercado"], aEscolher: true, item: null },
    },
    {
      caso: "a edição tira a versão de antes: 82% → 87%",
      antes: lancamento({ id: "feira", valor_centavos: 10000 }),
      depois: lancamento({ id: "feira", valor_centavos: 15000 }),
      aviso: { mes: OUT, categoriasComItem: ["mercado"], aEscolher: false, item: { categoria_id: "mercado", planejado_centavos: 100000, antes: estado(82, 18000), depois: estado(87, 13000) } },
    },
    {
      caso: "trocar a escolha leva o valor para o outro item",
      antes: lancamento({ id: "jantar", valor_centavos: 10000, categoria_ids: ["mercado", "casa"], item_categoria_id: "mercado" }),
      depois: lancamento({ id: "jantar", valor_centavos: 10000, categoria_ids: ["mercado", "casa"], item_categoria_id: "casa" }),
      aviso: { mes: OUT, categoriasComItem: ["mercado", "casa"], aEscolher: false, item: { categoria_id: "casa", planejado_centavos: 50000, antes: estado(30, 35000), depois: estado(50, 25000) } },
    },
    {
      caso: "o estorno diminui o item",
      depois: lancamento({ valor_centavos: 2000, estorno_de: "compra" }),
      aviso: { mes: OUT, categoriasComItem: ["mercado"], aEscolher: false, item: { categoria_id: "mercado", planejado_centavos: 100000, antes: estado(82, 18000), depois: estado(80, 20000) } },
    },
    {
      caso: "o a escolher editado sem escolha fica no item em que estava",
      planejamento: comAEscolher,
      antes: lancamento({ id: "ambiguo", valor_centavos: 2000, categoria_ids: ["mercado", "casa"] }),
      depois: lancamento({ id: "ambiguo", valor_centavos: 3000, categoria_ids: ["mercado", "casa"] }),
      aviso: { mes: OUT, categoriasComItem: ["mercado", "casa"], aEscolher: true, item: { categoria_id: "mercado", planejado_centavos: 100000, antes: estado(82, 18000), depois: estado(83, 17000) } },
    },
    {
      caso: "a edição que vem de outro mês entra inteira",
      antes: lancamento({ id: "compra", valor_centavos: 10000, mes: NOV }),
      depois: lancamento({ id: "compra", valor_centavos: 10000 }),
      aviso: { mes: OUT, categoriasComItem: ["mercado"], aEscolher: false, item: { categoria_id: "mercado", planejado_centavos: 100000, antes: estado(82, 18000), depois: estado(92, 8000) } },
    },
  ];
  for (const c of casos) {
    test(c.caso, () => {
      expect(avisoDePlanejamento(c.planejamento ?? outubro, c.antes ?? null, c.depois)).toEqual(c.aviso);
    });
  }

  test("sem o planejamento do mês em que o lançamento conta, não há aviso", () => {
    expect(avisoDePlanejamento(outubro, null, lancamento({ valor_centavos: 5000, mes: NOV }))).toBeNull();
  });

  test("sem mês (cartão sem fatura escolhida), não há aviso", () => {
    expect(avisoDePlanejamento(outubro, null, lancamento({ valor_centavos: 5000, mes: null }))).toBeNull();
  });
});

test.describe("planejamento com a fila por cima", () => {
  const item = (p: Planejamento, categoria: string) => p.itens.find((i) => i.categoria_id === categoria)!;

  test("o não enviado novo soma no item e no que ainda dá para gastar do mês", () => {
    const p = comAFila(outubro, [{ depois: lancamento({ id: "padaria", valor_centavos: 5000 }) }]);
    expect(item(p, "mercado")).toMatchObject({ realizado_centavos: 87000, percentual: 87, ainda_da_para_gastar_centavos: 13000 });
    expect(p.ainda_da_para_gastar_centavos).toBe(48000);
  });

  test("o item estourado não abate o que ainda dá para gastar do mês, e o ajuste de fatura sim", () => {
    const p = comAFila({ ...outubro, ajustes_de_fatura_centavos: 1000 }, [{ depois: lancamento({ id: "padaria", valor_centavos: 30000 }) }]);
    expect(item(p, "mercado").ainda_da_para_gastar_centavos).toBe(-12000);
    expect(p.ainda_da_para_gastar_centavos).toBe(34000);
  });

  test("o ajuste de fatura maior que o que sobra deixa o ainda dá para gastar negativo, sem parar em zero", () => {
    const p = comAFila({ ...outubro, ajustes_de_fatura_centavos: 60000 }, [{ depois: lancamento({ id: "padaria", valor_centavos: 30000 }) }]);
    expect(p.ainda_da_para_gastar_centavos).toBe(-25000);
  });

  test("a exclusão não enviada tira a versão do servidor", () => {
    const p = comAFila(outubro, [{ antes: lancamento({ id: "feira", valor_centavos: 2000 }) }]);
    expect(item(p, "mercado")).toMatchObject({ realizado_centavos: 80000, percentual: 80 });
  });

  test("a edição para outro mês sai deste", () => {
    const p = comAFila(outubro, [{ antes: lancamento({ id: "feira", valor_centavos: 2000, categoria_ids: ["casa"], situacao: "previsto" }), depois: lancamento({ id: "feira", valor_centavos: 2000, categoria_ids: ["casa"], mes: NOV }) }]);
    expect(item(p, "casa")).toMatchObject({ realizado_centavos: 10000, previsto_centavos: 3000, percentual: 26 });
  });

  test("o não enviado com duas categorias com item e sem escolha entra em a escolher", () => {
    const p = comAFila(outubro, [{ depois: lancamento({ id: "jantar", valor_centavos: 2000, categoria_ids: ["mercado", "casa"] }) }]);
    expect(p.a_escolher).toEqual([{ lancamento_id: "jantar", item_categoria_id: null, categorias_com_item: ["casa", "mercado"] }]);
    expect(item(p, "mercado").realizado_centavos).toBe(82000);
  });

  test("escolher o item tira o lançamento de a escolher", () => {
    const p = comAFila(comAEscolher, [{ antes: lancamento({ id: "ambiguo", valor_centavos: 2000, categoria_ids: ["mercado", "casa"] }), depois: lancamento({ id: "ambiguo", valor_centavos: 2000, categoria_ids: ["mercado", "casa"], item_categoria_id: "casa" }) }]);
    expect(p.a_escolher).toEqual([]);
    expect(item(p, "mercado").realizado_centavos).toBe(80000);
    expect(item(p, "casa").realizado_centavos).toBe(12000);
  });
});

test.describe("última escolha para o conjunto", () => {
  const passado = [
    { categoria_ids: ["mercado", "casa"], item_categoria_id: "mercado", em: 1 },
    { categoria_ids: ["casa", "mercado", "lazer"], item_categoria_id: "casa", em: 3 },
    { categoria_ids: ["mercado", "casa"], item_categoria_id: null, em: 5 },
    { categoria_ids: ["mercado", "lazer"], item_categoria_id: "lazer", em: 9 },
  ];

  test("a mais recente entre os lançamentos que têm as categorias do conjunto", () => {
    expect(ultimaEscolha(["mercado", "casa"], passado, ["mercado", "casa"])).toBe("casa");
  });

  test("o lançamento com outra categoria com item é de outro conjunto", () => {
    expect(ultimaEscolha(["mercado", "casa"], passado, ["mercado", "casa", "lazer"])).toBe("mercado");
  });

  test("a escolha fora do conjunto não vale", () => {
    expect(ultimaEscolha(["mercado", "casa"], [{ categoria_ids: ["mercado", "casa", "lazer"], item_categoria_id: "lazer", em: 1 }], ["mercado", "casa"])).toBeNull();
  });

  test("sem escolha guardada para o conjunto, nenhuma", () => {
    expect(ultimaEscolha(["casa", "viagem"], passado, ["casa", "viagem"])).toBeNull();
  });
});

test.describe("mês em que o lançamento conta", () => {
  const nubank = { titular: { dia_fechamento: 25, mes_anterior_ao_fechamento: false }, faturas: [] };
  const casos: { caso: string; l: Parameters<typeof mesEmQueConta>[0]; anterior?: Parameters<typeof mesEmQueConta>[1]; cartao?: Parameters<typeof mesEmQueConta>[2]; mes: string | null }[] = [
    { caso: "na conta, o mês da data", l: { conta_id: "corrente", data: "2026-10-28" }, mes: "2026-10-01" },
    { caso: "no cartão, a fatura pela data", l: { conta_id: "nubank", data: "2026-10-28" }, cartao: nubank, mes: "2026-11-01" },
    { caso: "no cartão, a fatura escolhida à mão", l: { conta_id: "nubank", data: "2026-10-28", fatura_mes: "2026-12-01" }, cartao: nubank, mes: "2026-12-01" },
    { caso: "na edição sem mudar data nem cartão, o mês que o servidor deu", l: { conta_id: "nubank", data: "2026-10-28" }, anterior: { conta_id: "nubank", data: "2026-10-28", mes: "2026-10-01" }, cartao: nubank, mes: "2026-10-01" },
    { caso: "na edição que muda a data, a fatura da data nova", l: { conta_id: "nubank", data: "2026-10-20" }, anterior: { conta_id: "nubank", data: "2026-10-28", mes: "2026-11-01" }, cartao: nubank, mes: "2026-10-01" },
    { caso: "a parcela 3/10 que muda de data cai duas faturas depois da fatura da compra", l: { conta_id: "nubank", data: "2026-10-05" }, anterior: { conta_id: "nubank", data: "2026-10-06", mes: "2026-12-01", parcela: 3 }, cartao: nubank, mes: "2026-12-01" },
    { caso: "a parcela 3/10 que muda de cartão cai duas faturas depois da fatura da compra", l: { conta_id: "visa", data: "2026-10-28" }, anterior: { conta_id: "nubank", data: "2026-10-28", mes: "2027-01-01", parcela: 3 }, cartao: nubank, mes: "2027-01-01" },
    { caso: "cartão sem dia de fechamento e sem fatura escolhida: não se sabe", l: { conta_id: "antigo", data: "2026-10-20" }, cartao: { titular: { dia_fechamento: null }, faturas: [] }, mes: null },
  ];
  for (const c of casos) {
    test(c.caso, () => {
      expect(mesEmQueConta(c.l, c.anterior, c.cartao)).toBe(c.mes);
    });
  }
});

test.describe("criar enviado sem resposta", () => {
  const enviado = lancamento({ valor_centavos: 5000 });
  const depois = lancamento({ valor_centavos: 8000 });
  const mercado = (p: Planejamento) => p.itens.find((i) => i.categoria_id === "mercado")!.realizado_centavos;
  const mudanca = { depois, talvez: { tentadoEm: 1000, jaNoServidor: enviado } };

  test("planejamento lido antes do envio: o criar conta inteiro", () => {
    expect(mercado(comAFila(outubro, semContarDeNovo([mudanca], 999)))).toBe(82000 + 8000);
  });

  test("planejamento lido depois do envio: já traz o enviado, e a fila só troca pela versão do aparelho", () => {
    const lido = { ...outubro, itens: outubro.itens.map((i) => (i.categoria_id === "mercado" ? { ...i, realizado_centavos: 87000 } : i)) };
    expect(mercado(comAFila(lido, semContarDeNovo([mudanca], 1000)))).toBe(87000 - 5000 + 8000);
  });

  test("criar comum, sem talvez, não muda", () => {
    expect(mercado(comAFila(outubro, semContarDeNovo([{ depois }], 5000)))).toBe(90000);
  });
});

test.describe("o que sobra, na despesa, na receita e na transferência", () => {
  const casos: { tipo: "despesa" | "receita" | "transferencia"; centavos: number; texto: string }[] = [
    { tipo: "despesa", centavos: 18000, texto: "Ainda dá para gastar R$ 180,00" },
    { tipo: "despesa", centavos: 0, texto: "Chega ao limite do planejado" },
    { tipo: "despesa", centavos: -5000, texto: "Passa R$ 50,00 do planejado" },
    { tipo: "receita", centavos: 18000, texto: "Faltam R$ 180,00 para o planejado" },
    { tipo: "receita", centavos: 0, texto: "Chega ao planejado" },
    { tipo: "receita", centavos: -5000, texto: "R$ 50,00 acima do planejado" },
    // A transferência com categoria guarda dinheiro: o texto é o da receita (o que falta para o planejado).
    { tipo: "transferencia", centavos: 70000, texto: "Faltam R$ 700,00 para o planejado" },
    { tipo: "transferencia", centavos: 0, texto: "Chega ao planejado" },
    { tipo: "transferencia", centavos: -5000, texto: "R$ 50,00 acima do planejado" },
  ];
  for (const c of casos) {
    test(`${c.tipo} com ${c.centavos} centavos: ${c.texto}`, () => {
      expect(oQueSobra(c.tipo, c.centavos)).toBe(c.texto);
    });
  }
});

test.describe("aviso de planejamento da compra com partes (ADR 0022)", () => {
  // R$ 300 no Mercado e R$ 200 na Casa, numa compra só de R$ 500.
  const comPartes = lancamento({
    id: "compra",
    valor_centavos: 50000,
    categoria_ids: [],
    partes: [
      { id: "feira", valor_centavos: 30000, categoria_ids: ["mercado"] },
      { id: "panela", valor_centavos: 20000, categoria_ids: ["casa"] },
    ],
  });

  test("uma linha por parte, cada uma no item dela", () => {
    const [feira, panela] = avisosDasPartes(outubro, null, comPartes);
    expect(feira).toMatchObject({ parte_id: "feira", item: { categoria_id: "mercado", antes: estado(82, 18000), depois: estado(112, -12000) } });
    expect(panela).toMatchObject({ parte_id: "panela", item: { categoria_id: "casa", antes: estado(30, 35000), depois: estado(70, 15000) } });
  });

  test("a fila conta cada parte no item dela, e a parte com dois itens fica a escolher sozinha", () => {
    const ambigua = { ...comPartes, partes: [{ id: "feira", valor_centavos: 30000, categoria_ids: ["mercado", "casa"] }, comPartes.partes![1]] };
    const depois = comAFila(outubro, [{ depois: ambigua }]);
    expect(depois.itens.map((i) => i.realizado_centavos)).toEqual([82000, 30000]);
    expect(depois.a_escolher).toEqual([{ lancamento_id: "compra", parte_id: "feira", item_categoria_id: null, categorias_com_item: ["casa", "mercado"] }]);
  });
});
