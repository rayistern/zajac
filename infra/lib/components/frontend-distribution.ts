import * as fs from "node:fs";
import { Annotations, Duration } from "aws-cdk-lib";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3deploy from "aws-cdk-lib/aws-s3-deployment";
import { Construct } from "constructs";

export interface FrontendDistributionProps {
  bucket: s3.IBucket;
  assetPrefix: string;
  frontendAssetPath: string;
  apiLoadBalancer: elbv2.IApplicationLoadBalancer;
  certificate?: acm.ICertificate;
  customDomainName?: string;
}

export class FrontendDistribution extends Construct {
  public readonly distribution: cloudfront.Distribution;

  constructor(scope: Construct, id: string, props: FrontendDistributionProps) {
    super(scope, id);

    const distributionProps: cloudfront.DistributionProps = {
      defaultRootObject: "index.html",
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(props.bucket, {
          originPath: `/${props.assetPrefix}`,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      },
      additionalBehaviors: {
        "/api/*": {
          origin: new origins.LoadBalancerV2Origin(props.apiLoadBalancer, {
            protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
          }),
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy:
            cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        },
      },
      errorResponses: [
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: Duration.minutes(1),
        },
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: Duration.minutes(1),
        },
      ],
    };

    const resolvedDistributionProps: cloudfront.DistributionProps =
      props.customDomainName && props.certificate
        ? {
            ...distributionProps,
            domainNames: [props.customDomainName],
            certificate: props.certificate,
          }
        : distributionProps;

    this.distribution = new cloudfront.Distribution(
      this,
      "Distribution",
      resolvedDistributionProps,
    );

    if (fs.existsSync(props.frontendAssetPath)) {
      new s3deploy.BucketDeployment(this, "Deployment", {
        destinationBucket: props.bucket,
        sources: [s3deploy.Source.asset(props.frontendAssetPath)],
        destinationKeyPrefix: props.assetPrefix,
        distribution: this.distribution,
        distributionPaths: ["/*"],
      });
    } else {
      Annotations.of(this).addWarning(
        `Skipping frontend upload because '${props.frontendAssetPath}' does not exist. Build frontend and set -c frontendAssetPath=...`,
      );
    }
  }
}
