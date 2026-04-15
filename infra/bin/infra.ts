#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { InfraStack } from "../lib/infra-stack";

const awsEnv: cdk.Environment = {
  account: process.env.CDK_DEFAULT_ACCOUNT || "671285285244",
  region: process.env.AWS_REGION || "us-east-1",
};

const app = new cdk.App();
const environmentName = app.node.tryGetContext("environmentName") ?? "staging";
const normalizedEnvironmentName = String(environmentName)
  .toLowerCase()
  .replace(/[^a-z0-9-]/g, "-")
  .replace(/^-+|-+$/g, "");
const domainName = app.node.tryGetContext("domainName");
const cloudFrontCertificateArn = app.node.tryGetContext(
  "cloudFrontCertificateArn",
);
// Pre-created Secrets Manager ARN for the Vercel AI Gateway key. Pass via
// `cdk deploy -c aiGatewaySecretArn=arn:aws:secretsmanager:...` OR via the
// AI_GATEWAY_SECRET_ARN env var in CI. The secret value itself MUST already
// exist before deploy — we only wire the reference.
const aiGatewaySecretArn =
  app.node.tryGetContext("aiGatewaySecretArn") ??
  process.env.AI_GATEWAY_SECRET_ARN;
const stackId = `InfraStack-${normalizedEnvironmentName}`;

const infraStack = new InfraStack(app, stackId, {
  env: awsEnv,
  environmentName: normalizedEnvironmentName,
  domainName,
  cloudFrontCertificateArn,
  aiGatewaySecretArn,
});

// Tag all resources for cost tracking
cdk.Tags.of(infraStack).add("Project", "merkos-rambam");
const tagEnvironment =
  normalizedEnvironmentName === "production"
    ? "prod"
    : normalizedEnvironmentName === "staging"
      ? "staging"
      : "preview";
cdk.Tags.of(infraStack).add("Environment", tagEnvironment);
