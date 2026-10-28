import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { App } from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { PilhaApp } from "../lib/pilha-app.js";
import { PilhaDados } from "../lib/pilha-dados.js";

test("alarme de 5xx da API acima do limite por dia avisa o dono por e-mail", () => {
  const app = new App();
  const env = { account: "123456789012", region: "sa-east-1" };
  const dados = new PilhaDados(app, "dados", { env, guardar: false });
  const pasta = mkdtempSync(join(tmpdir(), "pilha-"));
  const pilha = new PilhaApp(app, "app", {
    env,
    ambiente: "dev",
    dados,
    pacoteDaLambda: pasta,
    site: pasta,
    guardar: false,
    emailDoDono: "dono@example.com",
  });
  const modelo = Template.fromStack(pilha);
  modelo.hasResourceProperties("AWS::CloudWatch::Alarm", {
    MetricName: "5xx",
    Dimensions: Match.arrayWith([Match.objectLike({ Name: "Stage", Value: "$default" })]),
    Namespace: "AWS/ApiGateway",
    Statistic: "Sum",
    Period: 86400,
    EvaluationPeriods: 1,
    Threshold: 5,
    ComparisonOperator: "GreaterThanThreshold",
    TreatMissingData: "notBreaching",
    AlarmActions: [Match.anyValue()],
  });
  modelo.hasResourceProperties("AWS::SNS::Subscription", {
    Protocol: "email",
    Endpoint: "dono@example.com",
  });
});
