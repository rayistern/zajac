import * as cdk from "aws-cdk-lib";

export function removalPolicyFromStage(stage: string) {
  if (stageIsProdOrStaging(stage)) {
    return cdk.RemovalPolicy.RETAIN;
  }
  return cdk.RemovalPolicy.DESTROY;
}

export function stageIsProdOrStaging(
  stage: string,
): stage is "production" | "staging" {
  if (stage === "prod") {
    throw new Error("Use `production` instead of `prod` for production environments")
  }
  return stage === "production" || stage === "staging";
}
