import { existsSync } from "node:fs";
import { App } from "aws-cdk-lib";
import aws from "../../config/aws.json" with { type: "json" };
import { PilhaApp } from "../lib/pilha-app.js";
import { PilhaDados } from "../lib/pilha-dados.js";
import { PilhaOrcamento } from "../lib/pilha-orcamento.js";
import { PilhaGithub } from "../lib/pilha-github.js";

const app = new App();
// Região e conta só em configuração (config/aws.json).
const env = { account: aws.conta, region: aws.regiao };
const pacoteDaLambda = "../build/lambda"; // scripts/empacotar-lambda.sh
const site = "../web/dist"; // npm run build em web/

new PilhaGithub(app, "financial-github", {
  env,
  terminationProtection: true,
  subPrefixo: aws.github.subPrefixo,
});

// O orçamento é da conta, não de um ambiente.
new PilhaOrcamento(app, "financial-orcamento", { env, emailDoDono: aws.emailDoDono });

for (const ambiente of ["prod", "dev"] as const) {
  const guardar = ambiente === "prod";
  const dados = new PilhaDados(app, `financial-${ambiente}-dados`, {
    env,
    guardar,
    terminationProtection: guardar,
  });
  // Sem o pacote da Lambda e o build da PWA, só as pilhas sem código sintetizam
  // (é o caso do deploy da financial-github, feito à mão).
  if (existsSync(pacoteDaLambda) && existsSync(site)) {
    new PilhaApp(app, `financial-${ambiente}-app`, {
      env,
      ambiente,
      dados,
      pacoteDaLambda,
      site,
      guardar,
      emailDoDono: aws.emailDoDono,
      terminationProtection: guardar,
    });
  }
}
