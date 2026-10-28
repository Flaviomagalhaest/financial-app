import { CfnOutput, Duration, RemovalPolicy, Stack, type StackProps } from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as dsql from "aws-cdk-lib/aws-dsql";
import type { Construct } from "constructs";

export interface PilhaDadosProps extends StackProps {
  /** Em `prod` nada é apagado junto com a pilha; o `dev` é descartável. */
  guardar: boolean;
}

/**
 * O que guarda estado: o cluster do Aurora DSQL e o user pool do Cognito.
 * Fica numa pilha à parte para as migrations rodarem depois do banco e antes da Lambda nova.
 */
export class PilhaDados extends Stack {
  readonly banco: dsql.CfnCluster;
  readonly usuarios: cognito.UserPool;
  readonly clienteDoApp: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props: PilhaDadosProps) {
    super(scope, id, props);
    const remocao = props.guardar ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;

    this.banco = new dsql.CfnCluster(this, "Banco", {
      deletionProtectionEnabled: props.guardar,
    });
    this.banco.applyRemovalPolicy(remocao);
    // IDs fixos: a política da pilha (politicas/dados.json) proíbe substituir esses recursos.
    this.banco.overrideLogicalId("Banco");

    // Sem cadastro público: os dois usuários são criados à mão pelo dono (ADR 0002).
    this.usuarios = new cognito.UserPool(this, "Usuarios", {
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      featurePlan: cognito.FeaturePlan.LITE,
      accountRecovery: cognito.AccountRecovery.NONE,
      removalPolicy: remocao,
    });
    (this.usuarios.node.defaultChild as cognito.CfnUserPool).overrideLogicalId("Usuarios");

    // Cliente público (sem segredo) com SRP; sessão de anos e acesso de 15 minutos (ADR 0010).
    this.clienteDoApp = this.usuarios.addClient("ClienteDoApp", {
      generateSecret: false,
      authFlows: { userSrp: true },
      accessTokenValidity: Duration.minutes(15),
      idTokenValidity: Duration.minutes(15),
      refreshTokenValidity: Duration.days(3650),
      preventUserExistenceErrors: true,
    });

    new CfnOutput(this, "DsqlEndpoint", { value: this.banco.attrEndpoint });
    new CfnOutput(this, "UserPoolId", { value: this.usuarios.userPoolId });
    new CfnOutput(this, "ClienteDoAppId", { value: this.clienteDoApp.userPoolClientId });
  }
}
