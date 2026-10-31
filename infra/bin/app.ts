import { existsSync } from "node:fs";
import { App } from "aws-cdk-lib";
import aws from "../../config/aws.json" with { type: "json" };
import { PilhaApp } from "../lib/pilha-app.js";
import { PilhaDados } from "../lib/pilha-dados.js";
import { PilhaOrcamento } from "../lib/pilha-orcamento.js";
import { PilhaGithub } from "../lib/pilha-github.js";

// O repositório é público: a conta e o e-mail do dono vêm do ambiente (secrets `AWS_CONTA` e
// `EMAIL_DO_DONO` no deploy; variáveis exportadas na máquina do dono nos deploys à mão).
function exigir(nome: string): string {
  const valor = process.env[nome];
  if (!valor) throw new Error(`Falta a variável de ambiente ${nome} (veja o README, seção Deploy)`);
  return valor;
}

const app = new App();
// A região fica em config/aws.json.
const env = { account: exigir("AWS_CONTA"), region: aws.regiao };
const emailDoDono = exigir("EMAIL_DO_DONO");
// JSON `{"<sub>": "<nome>"}` das pessoas do casal em cada ambiente (ticket 84). Os `sub` não
// ficam no repositório: vêm da variável `PESSOAS` do GitHub Environment (ou do shell, à mão).
const pessoas = process.env.PESSOAS || undefined;
const pacoteDaLambda = "../build/lambda"; // scripts/empacotar-lambda.sh
const site = "../web/dist"; // npm run build em web/

new PilhaGithub(app, "financial-github", {
  env,
  terminationProtection: true,
  subPrefixo: aws.github.subPrefixo,
});

// O orçamento é da conta, não de um ambiente.
new PilhaOrcamento(app, "financial-orcamento", { env, emailDoDono });

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
      emailDoDono,
      pessoas,
      terminationProtection: guardar,
    });
  }
}
