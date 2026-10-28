import { CfnOutput, Duration, RemovalPolicy, Stack, type StackProps } from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as dsql from "aws-cdk-lib/aws-dsql";
import * as iam from "aws-cdk-lib/aws-iam";
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
  /** Role da Lambda; mora aqui para o deploy ligá-la ao papel `api` do banco antes da Lambda nova. */
  readonly roleDaApi: iam.Role;
  readonly usuarios: cognito.UserPool;
  readonly clienteDoApp: cognito.UserPoolClient;
  /** Emissor dos JWTs do user pool, conferido pela HTTP API e pela API. */
  readonly emissor: string;

  constructor(scope: Construct, id: string, props: PilhaDadosProps) {
    super(scope, id, props);
    const remocao = props.guardar ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;

    this.banco = new dsql.CfnCluster(this, "Banco", {
      deletionProtectionEnabled: props.guardar,
    });
    this.banco.applyRemovalPolicy(remocao);
    // IDs fixos: a política da pilha (politicas/dados.json) proíbe substituir esses recursos.
    this.banco.overrideLogicalId("Banco");

    // Só `dsql:DbConnect` (papel `api` do banco), nunca `DbConnectAdmin`.
    this.roleDaApi = new iam.Role(this, "RoleDaApi", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"),
      ],
    });
    this.roleDaApi.addToPolicy(
      new iam.PolicyStatement({
        actions: ["dsql:DbConnect"],
        resources: [this.banco.attrResourceArn],
      }),
    );

    // A pilha do app antiga ainda importa este export; o CloudFormation recusa removê-lo antes
    // de ela ser atualizada (o deploy dos dados vem primeiro). Pode sair num deploy futuro.
    this.exportValue(this.banco.attrResourceArn);

    // Sem cadastro público: os dois usuários são criados à mão pelo dono (ADR 0002).
    this.usuarios = new cognito.UserPool(this, "Usuarios", {
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      featurePlan: cognito.FeaturePlan.LITE,
      removalPolicy: remocao,
    });
    (this.usuarios.node.defaultChild as cognito.CfnUserPool).overrideLogicalId("Usuarios");

    // Cliente público (sem segredo) com SRP; sessão de anos e acesso de 15 minutos (ADR 0010).
    // O token de identidade também vale 15 minutos: a API aceita qualquer JWT do cliente, e
    // é esse o tempo que um celular perdido segue entrando depois de desconectado.
    this.clienteDoApp = this.usuarios.addClient("ClienteDoApp", {
      generateSecret: false,
      authFlows: { userSrp: true },
      accessTokenValidity: Duration.minutes(15),
      idTokenValidity: Duration.minutes(15),
      refreshTokenValidity: Duration.days(3650),
      enableTokenRevocation: true,
      preventUserExistenceErrors: true,
    });
    this.emissor = `https://cognito-idp.${this.region}.amazonaws.com/${this.usuarios.userPoolId}`;

    new CfnOutput(this, "DsqlEndpoint", { value: this.banco.attrEndpoint });
    new CfnOutput(this, "RoleDaApiArn", { value: this.roleDaApi.roleArn });
    new CfnOutput(this, "UserPoolId", { value: this.usuarios.userPoolId });
    new CfnOutput(this, "ClienteDoAppId", { value: this.clienteDoApp.userPoolClientId });
  }
}
