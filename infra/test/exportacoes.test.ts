import test from "node:test";
import { App } from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { PilhaDados } from "../lib/pilha-dados.js";

test("exportações a pedido ficam num bucket sem Object Lock e expiram em 7 dias", () => {
  const app = new App();
  const env = { account: "123456789012", region: "sa-east-1" };
  const modelo = Template.fromStack(new PilhaDados(app, "dados", { env, guardar: true }));

  modelo.hasResourceProperties("AWS::S3::Bucket", {
    LifecycleConfiguration: {
      Rules: [Match.objectLike({ ExpirationInDays: 7, Prefix: "exportacoes/", Status: "Enabled" })],
    },
    ObjectLockEnabled: Match.absent(),
  });
});
