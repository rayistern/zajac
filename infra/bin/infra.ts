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
const stackId = `InfraStack-${normalizedEnvironmentName}`;

const infraStack = new InfraStack(app, stackId, {
  env: awsEnv,
  environmentName: normalizedEnvironmentName,
  domainName,
  cloudFrontCertificateArn,
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
