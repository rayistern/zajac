import { RemovalPolicy } from "aws-cdk-lib";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";

export interface ContentStorageProps {
  /** Environment name for namespacing */
  environmentName: string;
}

/**
 * S3 bucket for pipeline-generated content images, served via CloudFront OAC.
 */
export class ContentStorage extends Construct {
  public readonly bucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: ContentStorageProps) {
    super(scope, id);

    this.bucket = new s3.Bucket(this, "ContentBucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: false,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy:
        props.environmentName === "production"
          ? RemovalPolicy.RETAIN
          : RemovalPolicy.DESTROY,
      autoDeleteObjects: props.environmentName !== "production",
      lifecycleRules: [
        {
          id: "abort-incomplete-multipart",
          abortIncompleteMultipartUploadAfter: { days: 7 } as any,
        },
      ],
    });
  }

  /**
   * Returns a CloudFront behavior config for serving content assets.
   * Use as an additional behavior on the main distribution.
   */
  public getCloudFrontBehavior(): cloudfront.BehaviorOptions {
    return {
      origin: origins.S3BucketOrigin.withOriginAccessControl(this.bucket),
      viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD,
    };
  }
}
