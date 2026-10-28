import {
  Annotations,
  CfnOutput,
  Duration,
  Fn,
  RemovalPolicy,
  Stack,
  type StackProps,
} from "aws-cdk-lib";
import * as apigw from "aws-cdk-lib/aws-apigatewayv2";
import { HttpJwtAuthorizer } from "aws-cdk-lib/aws-apigatewayv2-authorizers";
import { HttpLambdaIntegration } from "aws-cdk-lib/aws-apigatewayv2-integrations";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cwActions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3deploy from "aws-cdk-lib/aws-s3-deployment";
import * as sns from "aws-cdk-lib/aws-sns";
import * as subscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import * as triggers from "aws-cdk-lib/triggers";
import type * as dsql from "aws-cdk-lib/aws-dsql";
import type { Construct } from "constructs";
import type { PilhaDados } from "./pilha-dados.js";

export interface PilhaAppProps extends StackProps {
  ambiente: "prod" | "dev";
  dados: PilhaDados;
  /** Pasta com o pacote da Lambda (`scripts/empacotar-lambda.sh`). */
  pacoteDaLambda: string;
  /** Pasta com o build da PWA (`web/dist`). */
  site: string;
  /** Em `prod`, a distribuição fica mesmo se a pilha for apagada. */
  guardar: boolean;
  /** Quem recebe os alertas; sem ele, o tópico existe sem assinatura. */
  emailDeAlertas?: string;
}

/**
 * A PWA num S3 privado atrás do CloudFront, e `/api/*` no mesmo endereço indo à HTTP API
 * e a uma Lambda com a API inteira (ADR 0010). O backup diário usa o mesmo pacote (ADR 0012).
 */
export class PilhaApp extends Stack {
  constructor(scope: Construct, id: string, props: PilhaAppProps) {
    super(scope, id, props);
    const { banco, emissor, clienteDoApp, backup } = props.dados;

    const api = new lambda.Function(this, "Api", {
      runtime: lambda.Runtime.PYTHON_3_14,
      architecture: lambda.Architecture.ARM_64,
      handler: "app.lambda_handler.handler",
      code: lambda.Code.fromAsset(props.pacoteDaLambda),
      memorySize: 512,
      timeout: Duration.seconds(15),
      // A API confere o JWT de novo, só por emissor e audiência (app/login.py).
      environment: {
        DSQL_ENDPOINT: banco.attrEndpoint,
        JWT_EMISSOR: emissor,
        JWT_AUDIENCIA: clienteDoApp.userPoolClientId,
      },
      logGroup: new logs.LogGroup(this, "LogsDaApi", {
        retention: logs.RetentionDays.ONE_MONTH,
        removalPolicy: RemovalPolicy.DESTROY,
      }),
    });
    api.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["dsql:DbConnectAdmin"],
        resources: [banco.attrResourceArn],
      }),
    );

    // Só a rota de saúde é aberta; o resto exige o JWT do user pool (emissor e audiência).
    const httpApi = new apigw.HttpApi(this, "HttpApi", {
      createDefaultStage: false,
      defaultAuthorizer: new HttpJwtAuthorizer("Jwt", emissor, {
        jwtAudience: [clienteDoApp.userPoolClientId],
      }),
    });
    httpApi.addStage("Padrao", {
      stageName: "$default",
      autoDeploy: true,
      throttle: { rateLimit: 10, burstLimit: 20 },
    });
    const integracao = new HttpLambdaIntegration("Lambda", api);
    httpApi.addRoutes({
      path: "/api/saude",
      methods: [apigw.HttpMethod.GET],
      integration: integracao,
      authorizer: new apigw.HttpNoneAuthorizer(),
    });
    httpApi.addRoutes({
      path: "/api/{proxy+}",
      methods: [apigw.HttpMethod.ANY],
      integration: integracao,
    });

    const bucket = new s3.Bucket(this, "Site", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const distribuicao = new cloudfront.Distribution(this, "Distribuicao", {
      comment: `Financial App (${id})`,
      defaultRootObject: "index.html",
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(bucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      },
      additionalBehaviors: {
        // Mesmo endereço do app: sem CORS; sem cache, passando o Authorization à HTTP API.
        "/api/*": {
          origin: new origins.HttpOrigin(Fn.select(2, Fn.split("/", httpApi.apiEndpoint)), {
            protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
          }),
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        },
      },
    });
    // A PWA instalada fica presa a este endereço: o ID lógico é fixo e a política da pilha
    // (politicas/app.json) proíbe substituir ou remover a distribuição (ADR 0010).
    const cfnDistribuicao = distribuicao.node.defaultChild as cloudfront.CfnDistribution;
    cfnDistribuicao.overrideLogicalId("Distribuicao");
    cfnDistribuicao.applyRemovalPolicy(props.guardar ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY);

    new s3deploy.BucketDeployment(this, "PublicarSite", {
      sources: [s3deploy.Source.asset(props.site)],
      destinationBucket: bucket,
      distribution: distribuicao,
      distributionPaths: ["/*"],
      memoryLimit: 256,
    });

    this.backupDiario(props, banco, backup);

    new CfnOutput(this, "Endereco", { value: `https://${distribuicao.distributionDomainName}` });
  }

  /**
   * Todo dia o EventBridge chama a Lambda do backup, que grava o zip conferido no bucket com
   * Object Lock. Um e-mail avisa se ela falhar ou se passar 26 horas sem backup concluído.
   */
  private backupDiario(props: PilhaAppProps, banco: dsql.CfnCluster, bucket: s3.Bucket) {
    const funcao = new lambda.Function(this, "BackupDiario", {
      runtime: lambda.Runtime.PYTHON_3_14,
      architecture: lambda.Architecture.ARM_64,
      handler: "app.backup_diario.handler",
      code: lambda.Code.fromAsset(props.pacoteDaLambda),
      memorySize: 512,
      timeout: Duration.minutes(5),
      environment: {
        DSQL_ENDPOINT: banco.attrEndpoint,
        BACKUP_BUCKET: bucket.bucketName,
        AMBIENTE: props.ambiente,
      },
      logGroup: new logs.LogGroup(this, "LogsDoBackup", {
        retention: logs.RetentionDays.THREE_MONTHS,
        removalPolicy: RemovalPolicy.DESTROY,
      }),
    });
    funcao.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["dsql:DbConnectAdmin"],
        resources: [banco.attrResourceArn],
      }),
    );
    // Só grava zips novos: nem apaga nem mexe na retenção.
    funcao.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["s3:PutObject"],
        resources: [bucket.arnForObjects("diario/*")],
      }),
    );

    // 03:07 em São Paulo (06:07 UTC), fora do uso do casal.
    new events.Rule(this, "TodoDia", {
      schedule: events.Schedule.cron({ minute: "7", hour: "6" }),
      targets: [new targets.LambdaFunction(funcao)],
    });
    Annotations.of(funcao).acknowledgeWarning(
      "@aws-cdk/aws-lambda:addPermissionsToVersionOrAlias",
      "O EventBridge chama a função sem versão; o Trigger chama a versão com IAM em `:*`.",
    );
    // Cada deploy com código novo faz um backup e falha se ele falhar: o dev confere o
    // backup no DSQL de verdade antes do merge.
    new triggers.Trigger(this, "BackupNoDeploy", {
      handler: funcao,
      timeout: Duration.minutes(5),
    });

    const alertas = new sns.Topic(this, "Alertas", {
      displayName: `Financial App (${props.ambiente})`,
    });
    if (props.emailDeAlertas) {
      alertas.addSubscription(new subscriptions.EmailSubscription(props.emailDeAlertas));
    }
    const avisar = new cwActions.SnsAction(alertas);

    new cloudwatch.Alarm(this, "BackupFalhou", {
      alarmDescription: `O backup diário de ${props.ambiente} falhou (logs da Lambda ${funcao.functionName}).`,
      metric: funcao.metricErrors({ period: Duration.hours(1), statistic: "Sum" }),
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    }).addAlarmAction(avisar);

    // A Lambda publica `BackupsConcluidos` só depois de gravar o zip conferido
    // (backend/app/backup_diario.py). 26 horas seguidas sem ela: sem backup.
    new cloudwatch.Alarm(this, "BackupAtrasado", {
      alarmDescription: `Nenhum backup de ${props.ambiente} concluído nas últimas 26 horas.`,
      metric: new cloudwatch.Metric({
        namespace: "FinancialApp",
        metricName: "BackupsConcluidos",
        dimensionsMap: { Ambiente: props.ambiente },
        statistic: "Sum",
        period: Duration.hours(1),
      }),
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
      evaluationPeriods: 26,
      datapointsToAlarm: 26,
      treatMissingData: cloudwatch.TreatMissingData.BREACHING,
    }).addAlarmAction(avisar);

    new CfnOutput(this, "FuncaoDoBackup", { value: funcao.functionName });
  }
}
