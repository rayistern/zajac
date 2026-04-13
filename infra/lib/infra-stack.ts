import * as path from "node:path";
import { CfnOutput, Duration, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import { RemovalPolicy } from "aws-cdk-lib";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as ecsPatterns from "aws-cdk-lib/aws-ecs-patterns";
import * as logs from "aws-cdk-lib/aws-logs";
import * as rds from "aws-cdk-lib/aws-rds";
// import * as route53 from "aws-cdk-lib/aws-route53";
// import * as route53Targets from "aws-cdk-lib/aws-route53-targets";
import * as s3 from "aws-cdk-lib/aws-s3";
import { ContentStorage } from "./components/content-storage";
import { FrontendDistribution } from "./components/frontend-distribution";
import { RdsDatabase } from "./components/database";

export interface InfraStackProps extends StackProps {
  environmentName: string;
  domainName?: string;
  cloudFrontCertificateArn?: string;
}

export class InfraStack extends Stack {
  constructor(scope: Construct, id: string, props: InfraStackProps) {
    super(scope, id, props);

    const projectName = normalizeSlug("merkos-rambam");
    const projectConstructId = toConstructId(projectName);
    const databaseName = normalizeDatabaseName(projectName.replace(/-/g, "_"));
    const frontendAssetPath = path.resolve(__dirname, "../../frontend/dist");
    const workspaceRootPath = path.resolve(__dirname, "../../");

    const vpc = new ec2.Vpc(this, `${projectConstructId}Vpc`, {
      maxAzs: 2,
      natGateways: 0,
      subnetConfiguration: [
        {
          name: "Public",
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          name: "Application",
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
        {
          name: "Database",
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        },
      ],
    });

    vpc.addGatewayEndpoint(`${projectConstructId}S3GatewayEndpoint`, {
      service: ec2.GatewayVpcEndpointAwsService.S3,
    });

    const interfaceEndpointConfigs = [
      {
        idSuffix: "EcrApi",
        service: ec2.InterfaceVpcEndpointAwsService.ECR,
      },
      {
        idSuffix: "EcrDocker",
        service: ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
      },
      {
        idSuffix: "CloudWatchLogs",
        service: ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
      },
      {
        idSuffix: "SecretsManager",
        service: ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
      },
      {
        idSuffix: "Kms",
        service: ec2.InterfaceVpcEndpointAwsService.KMS,
      },
    ];

    interfaceEndpointConfigs.forEach(({ idSuffix, service }) => {
      vpc.addInterfaceEndpoint(
        `${projectConstructId}${idSuffix}InterfaceEndpoint`,
        {
          service,
        },
      );
    });

    const databaseSecurityGroup = new ec2.SecurityGroup(
      this,
      `${projectConstructId}DatabaseSecurityGroup`,
      {
        vpc,
        allowAllOutbound: false,
      },
    );

    const database = new RdsDatabase(this, `${projectConstructId}Database`, {
      projectName,
      vpc,
      stage: props.environmentName,
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_18_2,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T4G,
        ec2.InstanceSize.MICRO,
      ),
      credentials: rds.Credentials.fromGeneratedSecret("app_user"),
      securityGroups: [databaseSecurityGroup],
      databaseName,
      allocatedStorage: 20,
      maxAllocatedStorage: 100,
    });

    const cluster = new ecs.Cluster(this, `${projectConstructId}Cluster`, {
      vpc,
      containerInsightsV2: ecs.ContainerInsights.ENABLED,
    });

    const apiService = new ecsPatterns.ApplicationLoadBalancedFargateService(
      this,
      `${projectConstructId}ApiService`,
      {
        cluster,
        desiredCount: 1,
        minHealthyPercent: 100,
        publicLoadBalancer: true,
        cpu: 512,
        memoryLimitMiB: 1024,
        taskImageOptions: {
          image: ecs.ContainerImage.fromAsset(workspaceRootPath, {
            file: "api/Dockerfile",
          }),
          containerPort: 3000,
          environment: {
            APP_ENVIRONMENT: props.environmentName,
            DB_HOST: database.endpoint.hostname,
            DB_NAME: databaseName,
          },
          secrets: {
            DB_USER: ecs.Secret.fromSecretsManager(
              database.secret!,
              "username",
            ),
            DB_PASS: ecs.Secret.fromSecretsManager(
              database.secret!,
              "password",
            ),
          },
          logDriver: ecs.LogDrivers.awsLogs({
            streamPrefix: `${projectName}-api-${props.environmentName}`,
            logRetention: logs.RetentionDays.ONE_WEEK,
          }),
        },
      },
    );

    apiService.targetGroup.configureHealthCheck({
      path: "/",
      healthyHttpCodes: "200-399",
      interval: Duration.seconds(30),
    });

    database.instance.connections.allowDefaultPortFrom(apiService.service);

    const shouldConfigureCustomDomain =
      typeof props.domainName === "string" &&
      props.domainName.length > 0 &&
      typeof props.cloudFrontCertificateArn === "string" &&
      props.cloudFrontCertificateArn.length > 0;

    const certificate = shouldConfigureCustomDomain
      ? acm.Certificate.fromCertificateArn(
          this,
          `${projectConstructId}Certificate`,
          props.cloudFrontCertificateArn!,
        )
      : undefined;
    const resolvedDomainName = shouldConfigureCustomDomain
      ? props.domainName!
      : undefined;
    const customDomainName = resolvedDomainName
      ? props.environmentName === "production"
        ? resolvedDomainName
        : `${normalizeDnsLabel(props.environmentName)}.${resolvedDomainName}`
      : undefined;

    const contentStorage = new ContentStorage(
      this,
      `${projectConstructId}ContentStorage`,
      { environmentName: props.environmentName },
    );

    const frontendBucket = new s3.Bucket(this, "Bucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      autoDeleteObjects: true,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const frontendDistribution = new FrontendDistribution(
      this,
      `${projectConstructId}FrontendDistribution`,
      {
        bucket: frontendBucket,
        assetPrefix: `${projectName}/${props.environmentName}`,
        frontendAssetPath: frontendAssetPath,
        apiLoadBalancer: apiService.loadBalancer,
        customDomainName,
        certificate,
        additionalBehaviors: {
          "/content-assets/*": contentStorage.getCloudFrontBehavior(),
        },
      },
    );

    // const hostedZone = route53.HostedZone.fromLookup(
    //   this,
    //   `${projectConstructId}HostedZone`,
    //   {
    //     domainName: props.domainName,
    //   },
    // );
    // new route53.ARecord(this, `${projectConstructId}DistributionAliasRecord`, {
    //   zone: hostedZone,
    //   recordName: customDomainName,
    //   target: route53.RecordTarget.fromAlias(
    //     new route53Targets.CloudFrontTarget(frontendDistribution.distribution),
    //   ),
    // });
    // new route53.AaaaRecord(
    //   this,
    //   `${projectConstructId}DistributionAliasRecordIpv6`,
    //   {
    //     zone: hostedZone,
    //     recordName: customDomainName,
    //     target: route53.RecordTarget.fromAlias(
    //       new route53Targets.CloudFrontTarget(frontendDistribution.distribution),
    //     ),
    //   },
    // );

    new CfnOutput(this, `${projectConstructId}CloudFrontUrl`, {
      value: `https://${customDomainName ?? frontendDistribution.distribution.distributionDomainName}`,
    });

    new CfnOutput(this, `${projectConstructId}FrontendBucketName`, {
      value: frontendBucket.bucketName,
    });

    new CfnOutput(this, `${projectConstructId}ContentBucketName`, {
      value: contentStorage.bucket.bucketName,
    });

    new CfnOutput(this, `${projectConstructId}ApiAlbUrl`, {
      value: `http://${apiService.loadBalancer.loadBalancerDnsName}`,
    });

    new CfnOutput(this, `${projectConstructId}DatabaseSecretArn`, {
      value: database.secret!.secretArn,
    });

    new CfnOutput(this, `${projectConstructId}EnvironmentName`, {
      value: props.environmentName,
    });
  }
}

function normalizeSlug(value: string): string {
  const normalized = String(value)
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || "project";
}

function normalizeDnsLabel(value: string): string {
  const normalized = normalizeSlug(value).replace(/[^a-z0-9-]/g, "-");
  return normalized || "project";
}

function normalizeDatabaseName(value: string): string {
  const normalized = String(value)
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, "_")
    .replace(/^_+|_+$/g, "");
  const withLeadingLetter = /^[a-z]/.test(normalized)
    ? normalized
    : `db_${normalized}`;
  return (withLeadingLetter || "project_db").slice(0, 63);
}

function toConstructId(value: string): string {
  const words = String(value)
    .split(/[^a-zA-Z0-9]+/)
    .filter(Boolean);
  const result = words
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join("");
  return result || "Project";
}
