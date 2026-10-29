import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { App } from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { PilhaApp } from "../lib/pilha-app.js";
import { PilhaDados } from "../lib/pilha-dados.js";

test("a tarefa diária das recorrências roda logo depois da meia-noite de São Paulo e avisa se falhar", () => {
  const app = new App();
  const env = { account: "123456789012", region: "sa-east-1" };
  const dados = new PilhaDados(app, "dados", { env, guardar: false });
  const pasta = mkdtempSync(join(tmpdir(), "pilha-"));
  const pilha = new PilhaApp(app, "app", {
    env,
    ambiente: "prod",
    dados,
    pacoteDaLambda: pasta,
    site: pasta,
    guardar: false,
    emailDoDono: "dono@example.com",
  });
  const modelo = Template.fromStack(pilha);
  const funcoes = modelo.findResources("AWS::Lambda::Function", {
    Properties: { Handler: "app.tarefa_diaria.handler" },
  });
  const [funcao] = Object.keys(funcoes);
  if (!funcao) throw new Error("sem a Lambda da tarefa diária");
  modelo.hasResourceProperties("AWS::Scheduler::Schedule", {
    ScheduleExpression: "cron(7 0 * * ? *)",
    ScheduleExpressionTimezone: "America/Sao_Paulo",
    Target: Match.objectLike({
      Arn: { "Fn::GetAtt": [funcao, "Arn"] },
      RetryPolicy: Match.objectLike({ MaximumRetryAttempts: 2 }),
    }),
  });
  modelo.hasResourceProperties("AWS::CloudWatch::Alarm", {
    MetricName: "Errors",
    Dimensions: [{ Name: "FunctionName", Value: { Ref: funcao } }],
    Threshold: 1,
    AlarmActions: [Match.anyValue()],
  });
});
