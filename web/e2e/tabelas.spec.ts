// As regras que o app repete para o aviso de planejamento sem internet (ticket 52), contra as
// mesmas tabelas que `backend/tests/test_tabelas_compartilhadas.py` roda no servidor. Sem navegador.
import { expect, test } from "@playwright/test";
import ondeContaTabela from "../../tabelas-de-teste/onde-conta.json" with { type: "json" };
import percentualTabela from "../../tabelas-de-teste/percentual.json" with { type: "json" };
import mesDaCompraTabela from "../../tabelas-de-teste/mes-da-compra.json" with { type: "json" };
import { mesDaCompra, ondeConta, percentual } from "../src/dados/aviso";

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

test.describe("mês da compra no cartão", () => {
  for (const c of mesDaCompraTabela.casos) {
    test(c.caso, () => {
      expect(mesDaCompra(c.titular, c.faturas, c.data)).toBe(c.mes);
    });
  }
});
