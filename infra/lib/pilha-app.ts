import { CfnOutput, Duration, Fn, RemovalPolicy, Stack, type StackProps } from "aws-cdk-lib";
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
import type { Construct } from "constructs";
import type { PilhaDados } from "./pilha-dados.js";

export interface PilhaAppProps extends StackProps {
  dados: PilhaDados;
  /** Pasta com o pacote da Lambda (`scripts/empacotar-lambda.sh`). */
  pacoteDaLambda: string;
  /** Pasta com o build da PWA (`web/dist`). */
  site: string;
  /** Em `prod`, a distribuição fica mesmo se a pilha for apagada. */
  guardar: boolean;
  /** Recebe o alarme de erros 5xx da API. */
  emailDoDono: string;
}

/**
 * A PWA num S3 privado atrás do CloudFront, e `/api/*` no mesmo endereço indo à HTTP API
 * e a uma Lambda com a API inteira (ADR 0010).
 */
export class PilhaApp extends Stack {
  constructor(scope: Construct, id: string, props: PilhaAppProps) {
    super(scope, id, props);
    const { banco, roleDaApi, emissor, clienteDoApp } = props.dados;

    const api = new lambda.Function(this, "Api", {
      runtime: lambda.Runtime.PYTHON_3_14,
      architecture: lambda.Architecture.ARM_64,
      handler: "app.lambda_handler.handler",
      code: lambda.Code.fromAsset(props.pacoteDaLambda),
      role: roleDaApi,
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

    new CfnOutput(this, "Endereco", { value: `https://${distribuicao.distributionDomainName}` });
  }
}
