import { CfnOutput, Stack, type StackProps } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import type { Construct } from "constructs";

export interface PilhaGithubProps extends StackProps {
  /** `repo:DONO@ID/REPO@ID`, o formato novo e imutável do `sub` do GitHub. */
  subPrefixo: string;
}

/**
 * Provedor OIDC do GitHub e as roles que o workflow de deploy assume.
 * Publicada uma vez à mão (com credencial humana); depois disso o deploy sai só pelo Actions.
 *
 * Duas roles separadas por ambiente:
 *   - financial-app-deploy-prod: confia só no token gerado pelo GitHub Environment "prod"
 *     (protegido por regra de branch main-only no repositório), impedindo que qualquer
 *     branch acione um deploy de produção mesmo que altere o workflow.
 *   - financial-app-deploy-dev: confia em qualquer branch, para o dev contínuo.
 */
export class PilhaGithub extends Stack {
  constructor(scope: Construct, id: string, props: PilhaGithubProps) {
    super(scope, id, props);

    const provedor = new iam.OpenIdConnectProvider(this, "ProvedorGithub", {
      url: "https://token.actions.githubusercontent.com",
      clientIds: ["sts.amazonaws.com"],
    });

    const politicasComuns = (role: iam.Role) => {
      role.addToPolicy(
        new iam.PolicyStatement({
          actions: ["sts:AssumeRole"],
          resources: [`arn:aws:iam::${this.account}:role/cdk-hnb659fds-*-${this.account}-${this.region}`],
        }),
      );
      role.addToPolicy(
        new iam.PolicyStatement({
          actions: ["dsql:DbConnectAdmin"],
          resources: [`arn:aws:dsql:${this.region}:${this.account}:cluster/*`],
        }),
      );
      role.addToPolicy(
        new iam.PolicyStatement({
          actions: ["cloudformation:DescribeStacks", "cloudformation:SetStackPolicy"],
          resources: [`arn:aws:cloudformation:${this.region}:${this.account}:stack/financial-*/*`],
        }),
      );
    };

    // Role de prod: só aceita token gerado pelo GitHub Environment "prod" (sub termina em :environment:prod).
    // O GitHub só emite esse token para jobs que declaram `environment: prod` em branches autorizadas.
    const roleProd = new iam.Role(this, "RoleDeployProd", {
      roleName: "financial-app-deploy-prod",
      description: "Deploy de prod do Financial App pelo GitHub Actions (OIDC, environment prod)",
      assumedBy: new iam.WebIdentityPrincipal(provedor.openIdConnectProviderArn, {
        StringEquals: {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": `${props.subPrefixo}:environment:prod`,
        },
      }),
    });
    politicasComuns(roleProd);

    // Role de dev: aceita qualquer branch; nunca usada por jobs com environment: prod.
    const roleDev = new iam.Role(this, "RoleDeployDev", {
      roleName: "financial-app-deploy-dev",
      description: "Deploy de dev do Financial App pelo GitHub Actions (OIDC, qualquer branch)",
      assumedBy: new iam.WebIdentityPrincipal(provedor.openIdConnectProviderArn, {
        StringEquals: { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
        StringLike: { "token.actions.githubusercontent.com:sub": `${props.subPrefixo}:ref:refs/heads/*` },
      }),
    });
    politicasComuns(roleDev);

    new CfnOutput(this, "RoleDeployProdArn", { value: roleProd.roleArn });
    new CfnOutput(this, "RoleDeployDevArn", { value: roleDev.roleArn });
  }
}
