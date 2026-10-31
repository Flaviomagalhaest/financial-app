import {
  CfnOutput,
  Duration,
  Fn,
  RemovalPolicy,
  Stack,
  TimeZone,
  type StackProps,
} from "aws-cdk-lib";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cwactions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as apigw from "aws-cdk-lib/aws-apigatewayv2";
import { HttpJwtAuthorizer } from "aws-cdk-lib/aws-apigatewayv2-authorizers";
import { HttpLambdaIntegration } from "aws-cdk-lib/aws-apigatewayv2-integrations";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as sns from "aws-cdk-lib/aws-sns";
import * as subs from "aws-cdk-lib/aws-sns-subscriptions";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3deploy from "aws-cdk-lib/aws-s3-deployment";
import * as scheduler from "aws-cdk-lib/aws-scheduler";
import * as schedulerTargets from "aws-cdk-lib/aws-scheduler-targets";
import * as triggers from "aws-cdk-lib/triggers";
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
  /** Recebe o alarme de erros 5xx da API. */
  emailDoDono: string;
  /** JSON `{"<sub>": "<nome>"}` que vira a variável `PESSOAS` da API (app/pessoas.py). */
  pessoas?: string;
}

/**
 * A PWA num S3 privado atrás do CloudFront, e `/api/*` no mesmo endereço indo à HTTP API
 * e a uma Lambda com a API inteira (ADR 0010). O backup diário (ADR 0012) e a tarefa diária das
 * recorrências usam o mesmo pacote.
 */
export class PilhaApp extends Stack {
  constructor(scope: Construct, id: string, props: PilhaAppProps) {
    super(scope, id, props);
    const { banco, roleDaApi, emissor, clienteDoApp, exportacoes } = props.dados;

    const api = new lambda.Function(this, "Api", {
      runtime: lambda.Runtime.PYTHON_3_14,
      architecture: lambda.Architecture.ARM_64,
      handler: "app.lambda_handler.handler",
      code: lambda.Code.fromAsset(props.pacoteDaLambda),
      role: roleDaApi,
      memorySize: 512,
      // O "exportar tudo" lê o histórico inteiro e grava no S3; a HTTP API corta em 30 s.
      timeout: Duration.seconds(29),
      // A API confere o JWT de novo, só por emissor e audiência (app/login.py).
      environment: {
        DSQL_ENDPOINT: banco.attrEndpoint,
        JWT_EMISSOR: emissor,
        JWT_AUDIENCIA: clienteDoApp.userPoolClientId,
        EXPORTACOES_BUCKET: exportacoes.bucketName,
        ...(props.pessoas ? { PESSOAS: props.pessoas } : {}),
      },
      logGroup: new logs.LogGroup(this, "LogsDaApi", {
        retention: logs.RetentionDays.ONE_MONTH,
        removalPolicy: RemovalPolicy.DESTROY,
      }),
    });

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
    // Mais de 5 respostas 5xx num dia avisam o dono por e-mail.
    const avisos = new sns.Topic(this, "Avisos");
    avisos.addSubscription(new subs.EmailSubscription(props.emailDoDono));
    new cloudwatch.Alarm(this, "Erros5xx", {
      alarmDescription: "Erros 5xx da API acima do limite por dia",
      metric: new cloudwatch.Metric({
        namespace: "AWS/ApiGateway",
        metricName: "5xx",
        dimensionsMap: { ApiId: httpApi.apiId, Stage: "$default" },
        statistic: "Sum",
        period: Duration.days(1),
      }),
      threshold: 5,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    }).addAlarmAction(new cwactions.SnsAction(avisos));

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

    this.backupDiario(props, avisos);
    this.tarefaDiaria(props, avisos);

    new CfnOutput(this, "Endereco", { value: `https://${distribuicao.distributionDomainName}` });
  }

  /**
   * Todo dia o EventBridge Scheduler chama a Lambda do backup, que grava o zip conferido no bucket com
   * Object Lock. Um e-mail avisa se ela falhar ou se passar 26 horas sem backup concluído.
   */
  private backupDiario(props: PilhaAppProps, avisos: sns.Topic) {
    const { banco, roleDoBackup, backup } = props.dados;
    const funcao = new lambda.Function(this, "BackupDiario", {
      runtime: lambda.Runtime.PYTHON_3_14,
      architecture: lambda.Architecture.ARM_64,
      handler: "app.backup_diario.handler",
      code: lambda.Code.fromAsset(props.pacoteDaLambda),
      // Papel `backup` do banco, só leitura, e só grava zips novos no bucket (pilha de dados).
      role: roleDoBackup,
      memorySize: 512,
      timeout: Duration.minutes(5),
      environment: {
        DSQL_ENDPOINT: banco.attrEndpoint,
        BACKUP_BUCKET: backup.bucketName,
        AMBIENTE: props.ambiente,
      },
      logGroup: new logs.LogGroup(this, "LogsDoBackup", {
        retention: logs.RetentionDays.THREE_MONTHS,
        removalPolicy: RemovalPolicy.DESTROY,
      }),
    });

    // 03:07 em São Paulo, fora do uso do casal (ADR 0010: EventBridge Scheduler).
    new scheduler.Schedule(this, "TodoDia", {
      schedule: scheduler.ScheduleExpression.cron({
        minute: "7",
        hour: "3",
        timeZone: TimeZone.AMERICA_SAO_PAULO,
      }),
      target: new schedulerTargets.LambdaInvoke(funcao, { retryAttempts: 2 }),
    });
    // No dev, cada deploy com código novo faz um backup e falha se ele falhar: confere o
    // backup no DSQL de verdade antes do merge. Em prod não, para um backup quebrado não
    // travar o deploy de uma correção; lá o alarme avisa.
    if (props.ambiente === "dev") {
      new triggers.Trigger(this, "BackupNoDeploy", {
        handler: funcao,
        timeout: Duration.minutes(5),
      });
    }

    const avisar = new cwactions.SnsAction(avisos);

    new cloudwatch.Alarm(this, "BackupFalhou", {
      alarmDescription: `O backup diário de ${props.ambiente} falhou (logs da Lambda ${funcao.functionName}).`,
      metric: funcao.metricErrors({ period: Duration.hours(1), statistic: "Sum" }),
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    }).addAlarmAction(avisar);

    // A Lambda publica `BackupsConcluidos` só depois de gravar o zip conferido
    // (backend/app/backup_diario.py). Com 25 horas cheias sem ela, o alarme dispara até 26
    // horas depois do último backup (a hora do backup conta inteira).
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
      evaluationPeriods: 25,
      datapointsToAlarm: 25,
      treatMissingData: cloudwatch.TreatMissingData.BREACHING,
    }).addAlarmAction(avisar);

    new CfnOutput(this, "FuncaoDoBackup", { value: funcao.functionName });
  }

  /**
   * Logo depois da meia-noite de São Paulo, o EventBridge Scheduler chama a tarefa diária: ela
   * estende as recorrências até o horizonte e realiza os previstos automáticos do dia
   * (backend/app/tarefa_diaria.py). Um e-mail avisa se ela falhar; rodar de novo não duplica.
   */
  private tarefaDiaria(props: PilhaAppProps, avisos: sns.Topic) {
    const funcao = new lambda.Function(this, "TarefaDiaria", {
      runtime: lambda.Runtime.PYTHON_3_14,
      architecture: lambda.Architecture.ARM_64,
      handler: "app.tarefa_diaria.handler",
      code: lambda.Code.fromAsset(props.pacoteDaLambda),
      // Escreve nos lançamentos com o papel `api` do banco, como a API.
      role: props.dados.roleDaApi,
      memorySize: 512,
      timeout: Duration.minutes(5),
      environment: { DSQL_ENDPOINT: props.dados.banco.attrEndpoint },
      logGroup: new logs.LogGroup(this, "LogsDaTarefaDiaria", {
        retention: logs.RetentionDays.THREE_MONTHS,
        removalPolicy: RemovalPolicy.DESTROY,
      }),
    });

    // 00:07: o automático vira realizado no próprio dia, antes do backup das 03:07.
    new scheduler.Schedule(this, "TarefaTodoDia", {
      schedule: scheduler.ScheduleExpression.cron({
        minute: "7",
        hour: "0",
        timeZone: TimeZone.AMERICA_SAO_PAULO,
      }),
      target: new schedulerTargets.LambdaInvoke(funcao, { retryAttempts: 2 }),
    });

    new cloudwatch.Alarm(this, "TarefaDiariaFalhou", {
      alarmDescription: `A tarefa diária das recorrências de ${props.ambiente} falhou (logs da Lambda ${funcao.functionName}).`,
      metric: funcao.metricErrors({ period: Duration.hours(1), statistic: "Sum" }),
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    }).addAlarmAction(new cwactions.SnsAction(avisos));
  }
}
