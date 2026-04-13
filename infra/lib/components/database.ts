import { Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as rds from "aws-cdk-lib/aws-rds";
import * as kms from "aws-cdk-lib/aws-kms";
import { removalPolicyFromStage, stageIsProdOrStaging } from "./stage-utils";

export interface RdsDatabaseProps {
  projectName: string;
  vpc: ec2.IVpc;
  stage: string;
  /**
   * Defaults to initial 20 GiB, with scaling to 100 (via `maxAllocatedStorage`) for production environments.
   * Consider whether your application needs something different.
   */
  allocatedStorage?: number;
  /**
   * See documentation for `allocatedStorage`.
   */
  maxAllocatedStorage?: number;
  databaseName: string;
  credentials: rds.Credentials;
  engine: rds.IInstanceEngine;
  /**
   * This parameter does not affect preview environments,
   * use `previewInstanceType` for that.
   */
  instanceType: ec2.InstanceType;
  /**
   * The instance size to use in preview environments. If not specified, defaults to a small instance size.
   */
  previewInstanceType?: ec2.InstanceType;
  securityGroups: ec2.ISecurityGroup[];
  /**
   * Encryption is enabled by default using AWS-managed default keys.
   * Use this parameter if you need to use a customer managed key instead.
   */
  storageEncryptionKey?: kms.IKeyRef;
  multiAz?: boolean;
  availabilityZone?: string;
}

/**
 *
 */
export class RdsDatabase extends Construct {
  public readonly instance: rds.DatabaseInstance;
  public readonly arn: rds.DatabaseInstance["instanceArn"];
  public readonly endpoint: rds.DatabaseInstance["instanceEndpoint"];
  public readonly secret: rds.DatabaseInstance["secret"];

  constructor(scope: Construct, id: string, props: RdsDatabaseProps) {
    super(scope, id);

    this.instance = new rds.DatabaseInstance(
      this,
      `${props.projectName}-database`,
      {
        vpc: props.vpc,
        multiAz: props.multiAz,
        availabilityZone: props.availabilityZone,
        engine: props.engine,
        instanceType: stageIsProdOrStaging(props.stage)
          ? props.instanceType
          : (props.previewInstanceType ??
            ec2.InstanceType.of(ec2.InstanceClass.T4G, ec2.InstanceSize.MICRO)),
        databaseName: props.databaseName,
        credentials: props.credentials,
        securityGroups: props.securityGroups,
        // settings with defaults
        allocatedStorage: props.allocatedStorage ?? 20,
        maxAllocatedStorage:
          (props.maxAllocatedStorage ?? stageIsProdOrStaging(props.stage))
            ? 100
            : 20,
        // fixed settings
        // we would only ever need `ec2.SubnetType.PRIVATE_WITH_EGRESS` if we have need
        // to connect to other database, such as if we use foreign data wrappers.
        storageType: rds.StorageType.GP3,
        vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
        backupRetention: Duration.days(stageIsProdOrStaging(props.stage) ? 7 : 1),
        removalPolicy: removalPolicyFromStage(props.stage),
        deletionProtection: stageIsProdOrStaging(props.stage),
        publiclyAccessible: false,
        storageEncrypted: true,
        storageEncryptionKey: props.storageEncryptionKey,
      },
    );

    this.arn = this.instance.instanceArn;
    this.endpoint = this.instance.instanceEndpoint;
    this.secret = this.instance.secret;
  }
}
