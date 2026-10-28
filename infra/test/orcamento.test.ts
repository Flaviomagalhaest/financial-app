import assert from "node:assert/strict";
import test from "node:test";
import { App } from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { PilhaOrcamento } from "../lib/pilha-orcamento.js";

const email = "dono@example.com";

function sintetizar() {
  const app = new App();
  const pilha = new PilhaOrcamento(app, "orcamento", { emailDoDono: email });
  return Template.fromStack(pilha);
}

test("orçamento mensal sem créditos, com os três alertas por e-mail", () => {
  const modelo = sintetizar();
  modelo.resourceCountIs("AWS::Budgets::Budget", 1);
  modelo.hasResourceProperties("AWS::Budgets::Budget", {
    Budget: Match.objectLike({
      BudgetType: "COST",
      TimeUnit: "MONTHLY",
      BudgetLimit: { Amount: 5, Unit: "USD" },
      CostTypes: Match.objectLike({ IncludeCredit: false }),
    }),
  });
  const orcamento = Object.values(modelo.findResources("AWS::Budgets::Budget"))[0] as {
    Properties: { NotificationsWithSubscribers: Array<Record<string, any>> };
  };
  const alertas = orcamento.Properties.NotificationsWithSubscribers.map((n) => ({
    tipo: n.Notification.NotificationType,
    valor: n.Notification.Threshold,
    unidade: n.Notification.ThresholdType,
    emails: n.Subscribers.map((s: any) => s.Address),
  })).sort((a, b) => `${a.tipo}${a.valor}`.localeCompare(`${b.tipo}${b.valor}`));
  assert.deepEqual(alertas, [
    { tipo: "ACTUAL", valor: 1, unidade: "ABSOLUTE_VALUE", emails: [email] },
    { tipo: "ACTUAL", valor: 5, unidade: "ABSOLUTE_VALUE", emails: [email] },
    { tipo: "FORECASTED", valor: 5, unidade: "ABSOLUTE_VALUE", emails: [email] },
  ]);
});
