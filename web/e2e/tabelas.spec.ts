// As regras que o app repete para o aviso de planejamento sem internet (ticket 52) e para mostrar
// a divisão do parcelamento (ticket 98), contra as mesmas tabelas que
// `backend/tests/test_tabelas_compartilhadas.py` roda no servidor. Sem navegador.
import { expect, test } from "@playwright/test";
import ondeContaTabela from "../../tabelas-de-teste/onde-conta.json" with { type: "json" };
import percentualTabela from "../../tabelas-de-teste/percentual.json" with { type: "json" };
import mesDaCompraTabela from "../../tabelas-de-teste/mes-da-compra.json" with { type: "json" };
import divisaoTabela from "../../tabelas-de-teste/divisao-das-parcelas.json" with { type: "json" };
import puladasTabela from "../../tabelas-de-teste/puladas.json" with { type: "json" };
import { mesDaCompra, ondeConta, percentual } from "../src/dados/aviso";
import { dividirEmParcelas } from "../src/lancamentos/dinheiro";
import { ocorrenciasPuladas, parcelasPuladas } from "../src/lancamentos/puladas";
import type { RecorrenciaNaFolha } from "../src/lancamentos/recorrencia";

test.describe("onde conta", () => {
  for (const c of ondeContaTabela.casos) {
    test(c.caso, () => {
      expect(ondeConta(new Set(c.com_item), c.escolhida, c.atual)).toEqual([c.conta_em, c.a_escolher]);
    });
  }
});

test.describe("percentual", () => {
  for (const c of percentualTabela.casos) {
    test(c.caso, () => {
      expect(percentual(c.realizado_e_previsto, c.planejado)).toBe(c.percentual);
    });
  }
});

test.describe("divisão das parcelas", () => {
  for (const c of divisaoTabela.casos) {
    test(c.caso, () => {
      expect(dividirEmParcelas(c.total, c.parcelas)).toEqual({ primeira: c.primeira, outras: c.outras });
    });
  }
});

test.describe("mês da compra no cartão", () => {
  for (const c of mesDaCompraTabela.casos) {
    test(c.caso, () => {
      expect(mesDaCompra(c.titular, c.faturas, c.data)).toBe(c.mes);
    });
  }
});

test.describe("ocorrências puladas da recorrência", () => {
  for (const c of puladasTabela.recorrencias) {
    test(c.caso, () => {
      const regra: RecorrenciaNaFolha = {
        aCada: c.a_cada,
        unidade: c.unidade as RecorrenciaNaFolha["unidade"],
        fim: c.vezes ? "vezes" : c.ate ? "data" : "nunca",
        ate: c.ate ?? "",
        vezes: c.vezes ?? 2,
        tipoDoValor: "estimado",
        automatico: false,
      };
      expect(ocorrenciasPuladas(regra, c.inicio, c.hoje)).toBe(c.puladas);
    });
  }
});

test.describe("parcelas puladas do boleto", () => {
  for (const c of puladasTabela.parcelamentos) {
    test(c.caso, () => {
      expect(parcelasPuladas(c.parcelas, c.data, c.hoje, c.no_cartao)).toBe(c.puladas);
    });
  }
});
