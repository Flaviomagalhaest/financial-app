import { Stack, type StackProps } from "aws-cdk-lib";
import * as budgets from "aws-cdk-lib/aws-budgets";
import type { Construct } from "constructs";

export interface PilhaOrcamentoProps extends StackProps {
  emailDoDono: string;
}

/**
 * Orçamento mensal da conta, sem contar créditos para que eles não escondam o gasto.
 * Avisa o dono por e-mail em US$ 1 (real), US$ 5 (previsão) e US$ 5 (real).
 */
export class PilhaOrcamento extends Stack {
  constructor(scope: Construct, id: string, props: PilhaOrcamentoProps) {
    super(scope, id, props);
    const alerta = (
      tipo: "ACTUAL" | "FORECASTED",
      valor: number,
    ): budgets.CfnBudget.NotificationWithSubscribersProperty => ({
      notification: {
        notificationType: tipo,
        comparisonOperator: "GREATER_THAN",
        thresholdType: "ABSOLUTE_VALUE",
        threshold: valor,
      },
      subscribers: [{ subscriptionType: "EMAIL", address: props.emailDoDono }],
    });

    new budgets.CfnBudget(this, "Orcamento", {
      budget: {
        budgetType: "COST",
        timeUnit: "MONTHLY",
        budgetLimit: { amount: 5, unit: "USD" },
        costTypes: { includeCredit: false },
      },
      notificationsWithSubscribers: [
        alerta("ACTUAL", 1),
        alerta("FORECASTED", 5),
        alerta("ACTUAL", 5),
      ],
    });
  }
}
