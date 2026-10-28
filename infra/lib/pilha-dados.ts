import { CfnOutput, Duration, RemovalPolicy, Stack, type StackProps } from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as dsql from "aws-cdk-lib/aws-dsql";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import type { Construct } from "constructs";

export interface PilhaDadosProps extends StackProps {
  /** Em `prod` nada é apagado junto com a pilha; o `dev` é descartável. */
  guardar: boolean;
}

/**
 * O que guarda estado: o cluster do Aurora DSQL, o user pool do Cognito e o bucket do backup.
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
  /** Backup diário, com versões e Object Lock em compliance (ADR 0012). */
  readonly backup: s3.Bucket;
  /** Role da Lambda do backup, ligada ao papel `backup` do banco (só leitura) pelo deploy. */
  readonly roleDoBackup: iam.Role;

  constructor(scope: Construct, id: string, props: PilhaDadosProps) {
    super(scope, id, props);
    const remocao = props.guardar ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;

    this.banco = new dsql.CfnCluster(this, "Banco", {
      deletionProtectionEnabled: props.guardar,
    });
    this.banco.applyRemovalPolicy(remocao);
    // IDs fixos: a política da pilha (politicas/dados.json) proíbe substituir esses recursos
    // (o banco, o user pool e o bucket do backup).
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

    // Em compliance, nem o root apaga uma versão antes do prazo. O `dev` trava por 1 dia, para
    // o bucket dele não ficar preso e para se ver em poucos dias que o ciclo de vida apaga.
    const retencao = Duration.days(props.guardar ? 90 : 1);
    this.backup = new s3.Bucket(this, "Backup", {
      versioned: true,
      objectLockEnabled: true,
      objectLockDefaultRetention: s3.ObjectLockRetention.compliance(retencao),
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      // Com objetos travados o CloudFormation não consegue apagar o bucket; ele se esvazia
      // sozinho pelo ciclo de vida.
      removalPolicy: RemovalPolicy.RETAIN,
      lifecycleRules: [
        // Vencido o prazo, a versão atual ganha um marcador de exclusão e vira antiga, e a
        // antiga é apagada no dia seguinte. Enquanto a versão está travada, o ciclo de vida
        // não a apaga e tenta de novo depois.
        {
          id: "ApagarDepoisDoPrazo",
          expiration: retencao,
          noncurrentVersionExpiration: Duration.days(1),
        },
        { id: "LimparMarcadoresSemVersao", expiredObjectDeleteMarker: true },
      ],
    });
    (this.backup.node.defaultChild as s3.CfnBucket).overrideLogicalId("Backup");

    // Lê o banco pelo papel `backup` e só grava zips novos: nem apaga nem mexe na retenção.
    this.roleDoBackup = new iam.Role(this, "RoleDoBackup", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"),
      ],
    });
    this.roleDoBackup.addToPolicy(
      new iam.PolicyStatement({
        actions: ["dsql:DbConnect"],
        resources: [this.banco.attrResourceArn],
      }),
    );
    this.roleDoBackup.addToPolicy(
      new iam.PolicyStatement({
        actions: ["s3:PutObject"],
        resources: [this.backup.arnForObjects("diario/*")],
      }),
    );

    new CfnOutput(this, "DsqlEndpoint", { value: this.banco.attrEndpoint });
    new CfnOutput(this, "RoleDaApiArn", { value: this.roleDaApi.roleArn });
    new CfnOutput(this, "RoleDoBackupArn", { value: this.roleDoBackup.roleArn });
    new CfnOutput(this, "UserPoolId", { value: this.usuarios.userPoolId });
    new CfnOutput(this, "ClienteDoAppId", { value: this.clienteDoApp.userPoolClientId });
    new CfnOutput(this, "BucketDoBackup", { value: this.backup.bucketName });
  }
}
