import { CfnOutput, Stack, type StackProps } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import type { Construct } from "constructs";

export interface PilhaGithubProps extends StackProps {
  /** `repo:DONO@ID/REPO@ID`, o formato novo e imutável do `sub` do GitHub. */
  subPrefixo: string;
}

/**
 * Provedor OIDC do GitHub e a role que o workflow de deploy assume.
 * Publicada uma vez à mão (com credencial humana); depois disso o deploy sai só pelo Actions.
 */
export class PilhaGithub extends Stack {
  constructor(scope: Construct, id: string, props: PilhaGithubProps) {
    super(scope, id, props);

    const provedor = new iam.OpenIdConnectProvider(this, "ProvedorGithub", {
      url: "https://token.actions.githubusercontent.com",
      clientIds: ["sts.amazonaws.com"],
    });

    const role = new iam.Role(this, "RoleDeploy", {
      roleName: "financial-app-deploy",
      description: "Deploy do Financial App pelo GitHub Actions (OIDC)",
      assumedBy: new iam.WebIdentityPrincipal(provedor.openIdConnectProviderArn, {
        StringEquals: { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
        StringLike: { "token.actions.githubusercontent.com:sub": `${props.subPrefixo}:ref:refs/heads/*` },
      }),
    });

    // O CDK publica pelas roles do bootstrap; a role do Actions só as assume.
    role.addToPolicy(
      new iam.PolicyStatement({
        actions: ["sts:AssumeRole"],
        resources: [`arn:aws:iam::${this.account}:role/cdk-hnb659fds-*-${this.account}-${this.region}`],
      }),
    );
    // Migrations: o job de deploy entra no DSQL por IAM antes da Lambda nova.
    role.addToPolicy(
      new iam.PolicyStatement({
        actions: ["dsql:DbConnectAdmin"],
        resources: [`arn:aws:dsql:${this.region}:${this.account}:cluster/*`],
      }),
    );
    // Saídas das pilhas e a política que protege a distribuição do CloudFront.
    role.addToPolicy(
      new iam.PolicyStatement({
        actions: ["cloudformation:DescribeStacks", "cloudformation:SetStackPolicy"],
        resources: [`arn:aws:cloudformation:${this.region}:${this.account}:stack/financial-*/*`],
      }),
    );

    new CfnOutput(this, "RoleDeployArn", { value: role.roleArn });
  }
}
